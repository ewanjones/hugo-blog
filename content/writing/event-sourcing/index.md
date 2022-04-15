---
title: "Design your applications with events"
date: 2022-04-14T00:00:00+01:00
categories: [Tech]

---


## Let events be the source of truth


Anyone who knows me (professionally at least) knows I love event sourcing as a general practice when 
designing applications. We have been using a modified version of event sourcing at Octopus for 
a couple of years now to manage our industry processes, which often resemble  a conversation between 
us and multiple third parties.

I should prefix this post with a disclaimer that this is not a full-blown implementation of event
sourcing (more on that later) but it's a series of conventions that have helped us build robust and
scalable systems that have auditing built in. I've adapted this from the documentation I produced to 
help people get to grips with our code.


## Problem


In our previous message processing system, handlers were executing multiple actions 
synchronously. This  means that if an exception was raised mid way through processing, the rest of 
the handler would fail to run, leaving the application in a bad state. We'd often have to write 
one-off scripts to fix these accounts and, as we were scaling quickly and gaining more clients, it 
became impossible to manage.

In the UK energy industry, messages often contain incorrect or conflicting data or messages come in 
the wrong order and even not at all. There's lots of complex business logic controlling which
actions need to be taken and, of course, things can always fail. The trouble is when they did fail,
we had limited auditing of what the conditions were at the time.

We decided we needed a system which satisfied the following requirements:

- Recording that a message or action had occurred, along with all it's data, was top priority
- Any actions occurring as a result of the message should all be atomic and fail independently
- Actions should only execute once per single event (idempotency)
- Any failures should be recorded to maintain visibility and easily retried when the bug is fixed
- Any messages processed out of sync should maintain the order they were sent (this includes if 
processing somehow failed)
- The process should be auditable and be easy to debug for both tech and ops - we get a lot of 
questions relating to lack of knowledge about the specifications of flows


<br><hr><br>


## Getting started with the framework


We're in the process of making this an open-sourceable library, but for now it's more a collection
of useful functions and a set of unofficial conventions.

Also when I say 'process' in the following text, what I really mean is event-sourced object, it can
be anything where you want to track state.


### Overview


The general components of this framework are:

- **Commands** - the entry point into the process and is the API that is called by external sources, e.g. views or API endpoints.
- **Process or entity** - the DB models which act as a container for events and store a 'cached' latest state.
- **Event handlers** - the pub/sub module and allows us to build up a context and process state to pass into actions
- **Action** - a function which executes a side effect, e.g. sending comms or messages. Ideally, you'd want this to run the first time the event is recorded, but not again if the message was processed again.
- **Conditions** - these a functions take a process and are passed in when subscribing actions to events so that they only run if all the conditions evaluate to True.

The general flow of the framework is this:

1. Command is called and passed arguments are validated if provided by a user. An event is recorded on the process object.
2. When recording, the framework checks if the event has been recorded before and only if they 
haven't it'll check the `event_handlers` module for actions that need to be run. 
It records these on a `_side_effects` attribute of the event object. 
3. Back in the commands module, we call the build function, which will loop through all of the events 
in a process chronologically and a) set the state of the model and context and b) run any actions that are still included (both failed and not run)
4. If the action runs, the key is deleted, if it fails then the error message is recorded as the value and logged to sentry (unless it's an expected error).


### Data layer


Firstly, we need to define models in the data layer to hold the events. You can use the base classes defined in `octoenergy.data.event_sourcing`, which gives you an event registry to subscribe event handlers (will be explained later).

The 'process' model here is purely a container for events, it doesn't necessarily need to be a physical process, it could be an entity like a supply point. You can define fields in it, but they should all ideally be set from the `event_handlers` module. The idea is that the attributes are used for filtering and ‘caching’ metadata about the process to allow for easy processing.

```python
# data.package.models.py

from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from octoenergy.data import event_sourcing, accounts


class OrderEventType(models.TextChoices):
    # Capture all the possible events that can happen, as granular as possible using low-level
    # language
    INITIATED_BY_CUSTOMER  = "INITIATED_BY_CUSTOMER"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    WAREHOUSE_PROCESSING_STARTED = "WAREHOUSE_PROCESSING_STARTED"
    WAREHOUSE_PROCESSING_FINISHED = "WAREHOUSE_PROCESSING_FINISHED"
    PACKAGE_COLLECTED_BY_COURRIER = "PACKAGE_COLLECTED_BY_COURRIER"
    PACKAGE_DELIVERED = "PACKAGE_DELIVERED"


class Order(event_sourcing.BaseProcess):
    # link the process to whichever objects you like, or not at all
    account = models.ForeignKey("accounts.Account", on_delete=models.PROTECT)

    def record_initiated(self, account_number: accounts.Account, product_ids: list, occurred_at=None):
        # Record events using the method defined in the base class
        self.record_event(
            OrderEventType.INITIATED_BY_CUSTOMER,
            # TIP: Use dataclasses here to have a clear schema definition in the domain layer and
            # include a method to serialise and deserialise the data
            # (useful when following some kind of message or API spec)
            data={"account_number": account_number, "product_ids": product_ids},
            occurred_at=occurred_at,
        )


class OrderEvent(event_sourcing.BaseProcessEvent):
    process = models.ForeignKey(SomeProcess, related_name="events", on_delete=models.PROTECT)
    event_type = models.CharField(max_length=255, choices=SomeEventType.choices)
    data = JSONField(encoder=DjangoJSONEncoder, null=True)
    occurred_at = models.DateTimeField()

    def __repr__(self):
        # It's useful to define this for debugging
        return f"<OrderEvent id={self.id} type={self.event_type}>"
```

### Add the domain event handlers module


This is the main part of the event sourcing framework and allows us to see all the subscribed actions and state updates in one place.

Create a package which will house your domain code and create an `event_handlers.py` module. This module handles subscribing state handlers to events and running actions as well. We import the generic registry module to handle creating decorators.

The `build_process` function is responsible for setting process state and running actions. It runs through each event chronologically and builds up a Context object, which is either a dictionary or dataclass that can be instantiated at the beginning. Dataclasses are recommended for their typing validation and ability to add methods, but remember to make all the fields optional types as they'll be instantiated with nothing in it.
This just allows us to store data for use in actions so we don’t have to query different events or put them on the main process object. Warning though, the context only knows what happens before it. If you rely on data in an event that happens in the future, you'll need to explicitly query events.

The `has_side_effect` decorator takes a `conditions` keyword argument, which allows you to define functions which return a `bool` of whether they should run. They only execute as AND queries at the moment, but you can combine conditions in one function with `or` to meet more complex use-cases

```python
# domain.package.event_handlers.py

from dataclasses import dataclass
from typing import Optional
from octoenergy.data.process import models
from octoenergy.domain.event_sourcing import registry
from . import actions, conditions

# Context is a data structure which allows us to easily pass data throughout the process, so that
# later actions don't have to query the DB for the event. You can also derive data, for example,
# a flag that evaluates to True based on two events happening together or a specific value being
# present.
@dataclass
class OrderContext:
    # All attributes here should be defined as optional, as they're instantiated by the builder
    # at the begginning
    account_number: Optional[str] = None


# These decorators are defined in the base class and allow us to register handlers
handles_event = models.SomeProcess.handles_event
has_side_effect = models.SomeProcess.has_side_effect

# This function turns a process and it's events into state, and runs any pending actions
build_process = registry.create_process_builder(
    models.SomeProcess.event_handler_registry, context_creator=Context
)



@handles_event(models.SomeProcessEventType.INITIATED_BY_CUSTOMER)
@has_side_effect(actions.send_order_confirmed_email, conditions=[user_opted_in_for_comms])
def _handle_initiated(
    process: models.Order,
    event: models.OrderEvent,
    context: Context
) -> None:
    context.account_number = event.data.get("account_number")
```

```python
# domain.package.conditions.py

def user_opted_in_for_comms(process):
    return process.account.users.first().opted_in_for_comms

```

### Add the actions module


This module holds functionality that we only want to run once per event. This means if it runs successfully, the only way to run it again is to add its name into the appropriate `event.side_effects` dict (this uses some getter/setter magic to support older versions of the framework storing it in `event.data`). If something goes wrong, we catch the error and put it on that dict, so when you fix the bug, all you have to do is rebuild and kraken will attempt to run the action again.

By inheriting a custom exception from `BaseProcessError`, the generic event processing code knows this is an expected error and won’t log it to sentry. This allows us to stop spamming sentry and provide a more useful error message to ops on how to fix.

**Warning!** Using external models in actions is dangerous because their state can change from underneath you. It's better to capture all the data you need from the outside world to create a snapshot of it, and any changes should be recorded in a new event which clearly articulates what data changed why it needed changing.

```python
# domain.package.actions.py
from octoenergy.data.process import models
from octoenergy.domain.event_sourcing import registry

class OrderError(registry.BaseProcessError):
    # Inheriting from this base error and raising within an action allows the framework to
    # recognise this as an expected error, and won't log to sentry but will still log the error
    # message on the event.
    pass


def send_order_confirmed_email(
    process: models.Order,
    event: cos_gain.OrderEvent,
    context: "event_handlers.OrderContext",
) -> None:
    # do something here
    pass
```

### Add the commands module


This module is the entry point into the process. Anything that happens externally, whether an ops person clicks a button or a message is received, which call into this module to record the event.

It’s okay to do some user validation here, and return errors if you want to block them from completing this action, but it’s preferred (especially for messages) to make sure the data is recorded and then handle it separately (e.g. sending an error message back to the other industry participant). Always include the build process at the end, unless you want an action to run at a different time.

```python
# domain.package.commands.py

def create_order(account, products, occurred_at):
    # Do some validation on whether the user has initiated this order already
    existing_order = get_active_order(meter_point, products)
    if existing_order:
        raise OrderError("Existing order found")

    order = create_order(account, products)
    process.record_initiated(account.number, products, occurred_at=occurred_at)
    build_process(process)
```

## Conventions


This framework is not perfect and with the big learning curve for new developers, mistakes can easily
be made. I've seen similar implementations from colleagues go into infinite loops due accidentally 
recording data (such as the current datetime) which makes the event unique for each recording of it.
To prevent this, we've developed some unofficial and unenforced conventions.

**Events and commands**

- Event names should be past tense verbs
- Event names related directly to command or action names
- Event names should be low-level and domain-specific, don't try and abstract anything (e.g. send 
D0057 rather than send rejection). I think don't try and abstract anything too early.
- Commands should have imperative naming e.g. `handle_` and `record_`

**Actions**

- Actions should be atomic and do a single thing
- Exception handling is built into the framework, don't worry about catching everything as long as 
the error message is user friendly!
- Only use conditions for things that don’t change, basically a deterministic function. If you have 
conditions that rely on certain parts of the process then they can suddenly evaluate from False to True, leave you confused as to what state it was in at the time.
- Actions should have imperative naming e.g. `send_xxx_flow`

**Code organization and functionality**

- Explicitly list parameters for `record_*` methods or use dataclasses for versioning
- Rebuild should be able to start with a completely blank slate and build all state in event handlers
- Don’t trust any data on the process/aggregate
- Don't mutate the process in commands - do that in event handlers when you rebuild the process
- Keep commands thin - they shouldn’t fail!
- Pull in info from the outside world as early as possible.
- Don't refer to outside world in handlers, actions or conditions.


<br><hr><br>


## How is it different from event sourcing


If you were to find a system with full event sourcing then you might see some key differences.

For example, true event sourcing would store all the events in a global table, probably optimised
heavily for time series data. We currently split our event table up by process, to prevent any table
quickly getting too big and unweildy. The power of a global events table is that even though you 
system can be split up functionaly, any part could subscribe off another event without depending on
the code that publishes the event, which is great for keeping your code loosely coupled.

If the system is based on a microservice architecture, you might also see some kind of event bus which
publishes the event to every listening service. Our application is a monolith so we don't require
this, but we do use a task queue to allow asynchronous processes.

You can take this a step further by introducing `command query responsibility segregation` (CQRS).
Effectively this involves splitting your system into two parts, one which handles commands and records
them into an event store (and triggers the response actions) and the other which handles queries,
reading from a separate store, either a replica for the primary event database, or some kind of
state cache, which is regularly kept in sync by 'rebuilding' from the events. This brings other 
problems, like eventual consistency, but can be really powerful.


## Why should I use this?


Firstly, event sourcing makes the debugging process significantly easier. Every little thing that 
happens in the process is diligantly recorded, ensuring uniqueness. Making recording events the top 
priority means that no information is ever lost. The status of all outstanding actions is persistent, 
allowing us to fix the bug, ‘rebuild’ the process and attempt to retry the event. It’s made debugging 
and improving these processes much clearer and easier if used well.

Event sourcing is a powerful pattern for managing state in an application, as well as responding to 
changes in it. The source of truth is captured in a set of events and the application state is built 
from replaying them in chronological order. This allows us to not only view the current state, but 
also to rebuild an object up to any point in time. We can also trigger 'lactions' to run as a result 
of the event first being recorded, creating an easy framework for managing processes in which we 
need to respond to certain events or entities which have complex state changes.

**Pros**

- More visibility over health of state
- Actions can fail independently
- Easily fix state problems by rebuilding from events
- See state at different times by only rebuilding events up to that point

**Cons**

- Missing information in events require backfilling or defaults (API versioning problems)
- Some process actions don’t fit easily into an event e.g. customer needs a prepay card SSD - 3 days
  - `SSD_MINUS_THREE_DAYS` - Doesn’t describe the event
  - `PREPAY_KEY_REQUESTED` - That hasn’t happened yet though, until the action runs
- Care is needed when dealing with the outside world, e.g. models which can change from underneath us
