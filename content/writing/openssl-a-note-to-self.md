---
title: "OpenSSL - a note to self"
date: 2022-03-28T20:06:41+01:00
categories: [Tech]

summary: "
    I was recently working on a project implementing a HTTP REST framework with mutual TLS
    JWS message encryption, requiring lots of certificate requests. I know I'll forget this
    next time I need to do it, so this serves as a note to self.
"
---


## Requesting a certificate

You can generate a CSR with the following command

```
openssl req 
    -newkey rsa:2048  
    -keyout private.key  
    -out service.csr  
    -config service.conf
```

The config is slightly confusing but this one covers most of the common use cases. The publisher of
API should define an exact specification.


```
[ req ]
default_bits           = 2048
default_md             = sha256
distinguished_name     = req_distinguished_name
req_extensions         = req_ext
prompt                 = no

[ req_distinguished_name ]
countryName                     = GB
0.organizationName              = The Best Company
organizationalUnitName        = UIT
commonName                      = TLS_Cert

[req_ext]
subjectAltName = DNS:www.example.com
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, keyAgreement
```

For EC generated keys require params to be created:

```
openssl genpkey -genparam -algorithm ec -pkeyopt ec_paramgen_curve:P-256 > conf/ecparams.conf
```

You also need to add `-newkey ec:conf/ecparams.conf` when generating the request


## Certificate processing


Once you've got a certificate back, you need to run the following steps:

Convert to PEM format 

```
openssl x509 -inform DER -in Octoenergy_TLS....cer -outform PEM -out oe_tls.cer.pem
```


Decrypt your key, for JWS...

```
openssl [ec|rsa] -in encrypted_private.key -out private.key.pem
```

Extract public keys from the cert

```
openssl x509 -in service.cer.pem -pubkey -out eond_jws.key.pub
```




## Installing certificates into a browser


Sometimes you'll need to install a client certificate for a portal to allow you access. If the root
CA is not a trusted one then you'll also need to add the bundle

Form the chain, checking the subject and issuer to make sure the chain links up! Using the following
command will print out the details so you can check the root certificate is signed by itself.

```
openssl x509 -in path/to/file.pem -text

cat rootca.pem intermediate.pem > chain.pem
```

Now generate the certificate in PFX format using the key, certificate and cert chain which is required
for Mac.

```
openssl pkcs12 -export -out tdt.pfx -inkey tdt.key.pem -in tdt.cer.pem -certfile chain.pem
```

Install this PFX file into Keychain 'Login' items (Mac) or into IIS (Windows [guide](https://www.ssl.com/how-to/install-an-ssl-tls-certificate-in-iis-10/)) and then access the TDT site.
