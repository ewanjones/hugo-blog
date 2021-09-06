---
title: "Secrets of the energy industry tech - faster switching"
date: 2021-09-06T14:06:41+01:00

summary: "
    Big things are coming in the energy industry... how the digitisation of the switching process will bring real benefits to the customer.
"
---


> I work as a Lead Technical Developer at [Octopus Energy](https://octopus.energy/) mainly specialising in the market gateway features of our product called Kraken. Our job is to send and receive all the message to both the other parties in the market and also to your smart meter.
>
>I've been fascinated with the energy industry since I joined and want to talk about all the cool (mainly tech) things that are happening right now in the UK. This stuff is not written down in one place so just leaving it here for anyone that needs it.


## Watt the hell is going on here?


The systems that power the energy industry were created when the market was first decentralised (privatised) in 1989. There are many fascinating quirks about the technologies, protocols and processes they've used, including hard-wired networks into our office that, until recently, was not accessible from our AWS infrastructure!

To start with the gas and electricity systems have completely separate systems, with different implementations (one query API is a SOAP format). At least both of the use file transfer as their method of message delivery (I've seen email protocols (EDIFACT) used in some markets), but again one is comma separated and one is pipe separated, as if they're engaged in some kind of battle to be the best half of the industry.

What happens when you, say, execute a switch? As soon as you click the button, we start the process of creating your account. We fetch data from the industries, *try* and match the addresses across the electricity and gas systems. We validate all the data and then hold onto it for 10 minutes so that operations have a chance to withdraw the switch before we begin. We then collect these up and generate the first message to industry, which is really only a fragment of a message that we bundle up every 15 minutes and generate into 'flow files'.

With file transfer there's an inherent delay, with batch processing, sending and collection on the other side. It might be a few hours before anyone (or computer) has even seen your message. At best we get the acceptance by the end of the day, but usually it's the next.

Being a decentralised system, there are many different roles in the industry providing different services and caring about different parts of it. In my opinion, they went a bit too far when tendering for providers of APIs and network, which has created a maze of differing formats and destinations. Some gas flows go through the electricity network, that's how crazy it is.

The other massive issue with the energy industry right now, and one that isn't being addressed any time soon, is the multiple sources of truth across the different participants in the industry. It's hard enough as it is to understand and build applications to update the data in the central industry database (which is managed by 14 independent network operators), but we also have to send messages to all our other services updating them as well. In an ideal world, a central system would receive requests to update date (e.g. switch to a new supplier or update address) and everyone who is register to that metering point would be updated. When we want to check our system's data, we can check it against an API provided by the central system. Australia actually uses a similar process and it works really well.


## The future is bright


The industry is going through a massive, albeit slow, update at the moment to speed up the process of switching customers to different suppliers from 14 days (or 5 days for elec-only) to two working days. The Faster, More Reliable Switching (FMRS) project, after about 4 years, is at the stage of development and testing and is due to go live next year. That acceptance time goes down from 24 ish hours to about 10 minutes. Most of the wait is actually allowing the old supplier to object.

The project centralises the registration management and deprecates some of the file-based methods with a new HTTP REST API protected with mutual TLS authentication and JWS message signing, which is great considering some of the industry don't even use SFTP. The solution, apart from requiring lots of certificate management, it's pretty good.

The management of the project is extensive, with huge amount of evidence required to prove the systems capability. There's a few rounds of testing processes that we could have skipped and just made an easy entry test, then allowed development to continue until the final, more thoroug testing round. It's one of the biggest waterfall projects I've seen and they're using all the classic tools, namely JIRA and Service Now, despite them being essentially [the same product](https://www.atlassian.com/software/jira/service-management/comparison/jira-service-management-vs-servicenow).

The funny thing about the tech team at Octopus is that none of us really have a background in energy, so we've had to hire someone just to translate and digest the mountain of documentation and notes that's generated. What I'd really love to see, if anyone's ever organising a massive project like this, is a 'developers guide' which gives us all the specifications, schemas, and business logic as well as a simple overview of what each process is, especially if you're changing the technical jargon around it. One example is **disconnections**, the process of completely disconnecting a property from the grid and removing the MPAN (unique identifier) now has a parallel process in the new system called **deactivations**.


## Digital revolution


It's not perfect, but it's definitely a step in the right direction and brings real value to you, the customer. I'm also excited for the future projects coming up which will really bring our energy system into the 21st Century. Together with the smart meter rollout and all the home technology we have available to us, we can do do some really cool things to protect our energy grid. Check out the [octopus blog](https://octopus.energy/blog/) to see what else we've got going on!

If you fancy working for a company that's trying to make the world a better place, see if there's a [job for you](https://octopus.energy/careers/#/).
