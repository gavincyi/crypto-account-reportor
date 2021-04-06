import json
from datetime import datetime
import requests

import boto3

import ccxt

USD_BASE_CURRENCIES = ['USD', 'USDT', 'USDC']

CRYPTO_BASE_CURRENCIES = ['BTC']

SMALL_BALANCE = 1e-6

USD_RATES = None


def initialise_usd_rates(key):
    rates = requests.get('http://api.exchangeratesapi.io/v1/latest?access_key=%s' % key)
    rates['EUR'] = 1.0
    eur_usd = rates['USD']
    USD_RATES = {
        currency: rate * eur_usd 
        for currency, rate in rates.items()
    }


def get_usd_rate(currency):
    assert USD_RATES, "USD rates are not yet initialized"
    return USD_RATES[currency]


def get_usd_base_currency(exchange_tickers, currency):
    for base_currency in USD_BASE_CURRENCIES:
        if (currency + '/' + base_currency) in exchange_tickers:
            return currency + '/' + base_currency

    return None
    
    
def get_crypto_base_currency(exchange_tickers, currency):
    for base_currency in CRYPTO_BASE_CURRENCIES:
        if (currency + '/' + base_currency) in exchange_tickers:
            return currency + '/' + base_currency, base_currency
            
    return None, None


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
    crypto_exchange_keys = (
        client.scan(TableName='crypto-exchange-keys')['Items']
    )
    
    # Initialise the USD rates
    assert any([
        item['exchange']['S'] == 'exchangeratesapi' 
        for item in crypto_exchange_keys
    ]), "No exchangeratesapi key to initialise the USD rates"
    exchangeratesapi_key = [
        item['key']['S']
        for item in crypto_exchange_keys
        if item['exchange']['S'] == 'exchangeratesapi' 
    ][0]
    initialise_usd_rates(exchangeratesapi_key)
    print("USD rates are initialised as %s" % USD_RATES)
    
    # Iterate the crypto exchange keys
    crypto_exchange_keys = [
        item for item in crypto_exchange_keys
        if item['exchange']['S'] != 'exchangeratesapi' 
    ]

    for item in crypto_exchange_keys:
        exchange_name = item['exchange']['S']
        key = item['key']['S']
        secret = item['secret']['S']
        name = item['name']['S']
        exchange_params = {
            'apiKey': key,
            'secret': secret,
            'enableRateLimit': True,
        }
        if 'uid' in item:
            exchange_params['uid'] = item['uid']['S']
        exchange = getattr(ccxt, exchange_name.lower())(exchange_params)

        total_balances = {}

        if 'types' in item:
            for balance_type in item['types']['L']:
                balance_type = balance_type['S']
                total_balance = (
                    exchange.fetch_balance({'type': balance_type})['total']
                )
                total_balances[balance_type] = total_balance
        else:
            continue

        exchange_tickers = exchange.fetch_tickers()

        for balance_type, total_balance in total_balances.items():
            for currency, amount in total_balance.items():
                amount = float(amount)
                
                # Do not price the small balance
                if amount < SMALL_BALANCE:
                    continue
                
                usd_base_currency = (
                    get_usd_base_currency(exchange_tickers, currency)
                )
                crypto_base_currency, crypto_fiat = (
                    get_crypto_base_currency(exchange_tickers, currency)
                )
                if currency in USD_BASE_CURRENCIES:
                    usd_amount = amount
                elif usd_base_currency:
                    usd_amount = (
                        exchange_tickers[usd_base_currency]['close'] * amount
                    )
                elif crypto_base_currency:
                    usd_base_crypto_fiat = (
                        get_usd_base_currency(exchange_tickers, crypto_fiat)
                    )
                    usd_amount = (
                        exchange_tickers[crypto_base_currency]['close'] *
                        exchange_tickers[usd_base_crypto_fiat]['close'] *
                        amount
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
