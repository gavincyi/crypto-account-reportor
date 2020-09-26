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
--attribute-definitions AttributeName=name,AttributeType=S \
--key-schema AttributeName=name,KeyType=HASH \
--provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### Create table crypto-exchange-balance

```
aws dynamodb create-table \
--table-name crypto-exchange-balance \
--attribute-definitions AttributeName=id,AttributeType=S \
--key-schema AttributeName=id,KeyType=HASH \
--provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```


