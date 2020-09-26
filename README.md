# crypto-account-reportor

Crypto account report is a AWS SAM template project. Currently it supports to store the daily balance in each exchange in dynamodb.

## Requirement

- AWS SAM

- Docker (for testing)


## Installation

To build the app, run

```
sam build
```

To local invoke the app, e.g. update balance function, run

```
sam local invode "UpdateBalanceFunction" -e events/event.json
```

To deploy the app, run

```
sam deploy
```

## Preparation

### Create table crypto-exchange-keys 

```
aws dynamodb create-table \
--table-name crypto-exchange-keys \
--attribute-definitions AttributeName=name,AttributeType=string \
--key-schema AttributeName=name,KeyType=HASH
```

