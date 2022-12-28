import logging
import sys
import configparser
import click
from termcolor import colored
from elasticsearch_dsl import Search
import elasticsearch

logging.basicConfig(
    level=logging.CRITICAL,
    format="%(filename)s: "
           "%(levelname)s: "
           "%(funcName)s(): "
           "%(lineno)d:\t"
           "%(message)s",
)

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("kompare.ini")


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, default=False, help="Debug switch")
@click.pass_context
def cli(context, debug):
    import boto3

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if debug:
        logging.basicConfig(
            format="%(asctime)s : %(name)s %(levelname)s : %(message)s",
            level=logging.DEBUG,
        )
    else:
        logging.basicConfig(
            format="%(asctime)s : %(name)s %(levelname)s : %(message)s",
            level=logging.CRITICAL,
        )

    logging.debug("Debug ON")
    if len(sys.argv) == 1:
        click.echo(context.get_help())

    context.obj = {}
    context.obj['config'] = config

    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        context.obj['elastic'] = elasticsearch.Elasticsearch(config["elasticsearch"]["url"], verify_certs=False)
        context.obj['dynamodb'] = boto3.resource("dynamodb", endpoint_url=config["dynamodb"]["url"])


def check_elastic(elastic, table, eid, did, eid_value):
    return True


def check_dynamo(dynamodb, table, eid, did, eid_value):
    import boto3
    from boto3.dynamodb.conditions import Key

    table = dynamodb.Table(table)
    response = table.query(
        KeyConditionExpression=Key(did).eq(eid_value)
    )

    return response['Count'] > 0


def scan(table, **kwargs):
    response = table.scan(**kwargs)
    yield from response['Items']
    while response.get('LastEvaluatedKey'):
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'], **kwargs)
        yield from response['Items']


@cli.command(name="tables")
@click.pass_context
def list_tables(context):
    """ List dynamodb tables """
    import boto3

    dynamodb = context.obj['dynamodb']
    tables = list(dynamodb.tables.all())
    for table in tables:
        print(table.name)


@cli.command(name="indices")
@click.pass_context
def list_indices(context):
    """ List elasticsearch indices """
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = context.obj['elastic']

        indices = client.cat.indices(h='index', s='index').split()
        for index in indices:
            print(index)


@cli.command()
@click.option("-eid", required=True, help="ElasticSearch document id field name")
@click.option("-did", required=True, help="DynamoDB document id field name")
@click.option("-t", "--table", required=True, help="DynamoDB table")
@click.option("-i", "--index", required=True, help="ElasticSearch index")
@click.option("-c", "--csv", required=False, is_flag=True, default=False, help="Output all differences in CSV file")
@click.option("-o", "--out", required=False, default="kompare.out", help="CSV output filename")
@click.pass_context
def dyn2es(context, eid, did, table, index, csv, out):
    """Scan dynamodb and find matches in elasticsearch"""
    import boto3
    from prettytable import PrettyTable
    from progress.bar import Bar
    import warnings
    import csv

    x = PrettyTable()

    names = ["Dynamo Table", "ES Field", "DynamoDB Field", "Elastic Index", "Misses", "Total"]

    x.field_names = names

    with open(out, 'w') as csvfile:

        writer = csv.writer(csvfile)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            dynamodb = context.obj['dynamodb']
            _table = dynamodb.Table(table)
            _total = _table.item_count
            bar = Bar('Scanning', max=_total)
            dynamo_misses = 0
            for doc in scan(_table):
                did_value = doc[did]

                if not check_elastic(context.obj['elastic'], table, eid, did, did_value):
                    dynamo_misses += 1

                    writer.writerow([table, did, did_value])

                bar.next()

            x.add_row([table, index, eid, did, dynamo_misses, _total])
            print()
            print(x)


@cli.command()
@click.option("-eid", required=True, help="ElasticSearch document id field name")
@click.option("-did", required=True, help="DynamoDB document id field name")
@click.option("-t", "--table", required=True, help="DynamoDB table")
@click.option("-i", "--index", required=True, help="ElasticSearch index")
@click.option("-c", "--csv", required=False, is_flag=True, default=False, help="Output all differences in CSV file")
@click.option("-o", "--out", required=False, default="kompare.out", help="CSV output filename")
@click.pass_context
def es2dyn(context, eid, did, table, index, csv, out):
    """Scan elasticsearch and find matches in dynamodb"""
    from prettytable import PrettyTable
    from progress.bar import Bar
    import warnings
    import csv

    x = PrettyTable()

    names = ["Dynamo Table", "ES Field", "DynamoDB Field", "Elastic Index", "Misses", "Total"]

    x.field_names = names

    with open(out, 'w') as csvfile:

        writer = csv.writer(csvfile)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            client = context.obj['elastic']
            client.indices.refresh(index)
            total_docs = client.cat.count(index, params={"format": "json"})
            _total = int(total_docs[0]['count'])
            bar = Bar('Scanning', max=_total)

            search = Search(using=client, index=index)
            dynamo_misses = 0

            for hit in search.scan():
                if eid in hit:
                    eid_value = hit[eid]
                    if not check_dynamo(context.obj["dynamodb"], table, eid, did, eid_value):
                        dynamo_misses += 1

                        writer.writerow([table, did, eid_value])
                else:
                    logger.error(f"No field {eid} in {hit}")

                bar.next()

            x.add_row([table, index, eid, did, dynamo_misses, _total])
            print()
            print(x)
