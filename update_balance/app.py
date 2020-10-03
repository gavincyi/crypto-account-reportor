import json
from datetime import datetime
import requests

import boto3

import ccxt

USD_BASE_CURRENCIES = ['USD', 'USDT', 'USDC']


def get_usd_rate(currency):
    rates = requests.get('https://api.exchangeratesapi.io/latest').json()['rates']
    rates['EUR'] = 1.0
    eur_usd = rates['USD']
    return rates[currency] * eur_usd


def get_usd_base_currency(exchange_tickers, currency):
    for base_currency in USD_BASE_CURRENCIES:
        if (currency + '/' + base_currency) in exchange_tickers:
            return currency + '/' + base_currency

    return None


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """
    records = []
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    client = boto3.client('dynamodb')

    for item in client.scan(TableName='crypto-exchange-keys')['Items']:
        exchange_name = item['exchange']['S']
        key = item['key']['S']
        secret = item['secret']['S']
        name = item['name']['S']
        exchange = getattr(ccxt, exchange_name.lower())({
            'apiKey': key,
            'secret': secret,
            'enableRateLimit': True,
        })

        total_balances = {}

        if 'types' in item:
            for balance_type in item['types']['L']:
                balance_type = balance_type['S']
                total_balance = (
                    exchange.fetch_balance({'type': balance_type})['total']
                )
                total_balances[balance_type] = total_balance
        else:
            raise NotImplementedError(
                'Cannot work without balance type'
            )

        exchange_tickers = exchange.fetch_tickers()

        for balance_type, total_balance in total_balances.items():
            for currency, amount in total_balance.items():
                amount = float(amount)
                usd_base_currency = (
                    get_usd_base_currency(exchange_tickers, currency)
                )
                if currency in USD_BASE_CURRENCIES:
                    usd_amount = amount
                elif usd_base_currency:
                    usd_amount = (
                        exchange_tickers[usd_base_currency]['close'] * amount
                    )
                else:
                    usd_amount = (
                        get_usd_rate(currency) * amount
                    )

                records.append({
                    "id": {
                        'S': (
                            current_time
                            + '/' + exchange_name
                            + '/' + balance_type
                            + currency
                        )
                    },
                    "datetime": {'S': current_time},
                    "exchange": {'S': exchange_name},
                    "type": {'S': balance_type},
                    "currency": {'S': currency},
                    "amount": {'N': str(amount)},
                    "usd_amount": {'N': str(round(usd_amount, 2))},
                    "name": {'S': name},
                })

    for record in records:
        try:
            client.put_item(
                TableName='crypto-exchange-balance',
                Item=record
            )
        except Exception as e:
            print('Exception thrown in reocrd "%s" due to %s'
                  % (record, e))

    return {
        "statusCode": 200,
        "body": {"data": records},
    }
