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
sam deploy --guided
```

## Preparation

The following commands requires running the commands with `awscli`. Please
refer to the installation [guide](https://github.com/aws/aws-cli) for the
package in the interactive machines.

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

### Insert exchange accounts

First you need to create the exchange API keys first. It is highly recommended to create a 
**read-only** key for security.

Then amend the file `crypto-exchange-keys.json` on the following values

* name: An unique name of the key
* exchange: The exchange name, e.g. bitfinex
* key: The exchange API key
* secret: The exchange API secret
* types: A list of account types. For example, `spot` in Binance.

Then run the command to insert the exchange key.

```
aws dynamodb put-item --table-name crypto-exchange-keys --item file://crypto-exchange-keys.json 
```

