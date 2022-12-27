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


def check_dynamo(url, table, eid, did, eid_value):
    import boto3
    from boto3.dynamodb.conditions import Key

    dynamodb = boto3.resource("dynamodb", endpoint_url=url)
    table = dynamodb.Table(table)
    response = table.query(
        KeyConditionExpression=Key(did).eq(eid_value)
    )

    return response['Count'] > 0


@cli.command(name="ls")
@click.pass_context
def list_indices(context):
    """ List elasticsearch indices """
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = elasticsearch.Elasticsearch(context.obj["config"]["elasticsearch"]["url"], verify_certs=False)
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
def diff(context, eid, did, table, index, csv, out):
    """Display differences between elasticsearch and dynamodb"""
    from prettytable import PrettyTable
    from progress.bar import Bar

    x = PrettyTable()
    import warnings

    names = ["Dynamo Table","ES Field","DynamoDB Field","Elastic Index","Misses","Total"]

    x.field_names = names

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = elasticsearch.Elasticsearch(context.obj["config"]["elasticsearch"]["url"], verify_certs=False)
        client.indices.refresh(index)
        total_docs = client.cat.count(index, params={"format": "json"})
        _total = int(total_docs[0]['count'])
        bar = Bar('Scanning', max=_total)

        search = Search(using=client, index=index)
        dynamo_misses = 0

        for hit in search.scan():
            if eid in hit:
                eid_value = hit[eid]
                if not check_dynamo(context.obj["config"]["dynamodb"]["url"], table, eid, did, eid_value):
                    dynamo_misses += 1
            else:
                logger.error(f"No field {eid} in {hit}")

            bar.next()

        x.add_row([table,index,eid,did,dynamo_misses,_total])
        print()
        print(x)
        # Scan elasticsearch index for documents
        # Check eid field in each document
        # Search for document using did field in dynamo
        # If exists or not exists, record counts
        import csv

        # open the file in the write mode
        with open(out, 'w') as csvfile:

            # create the csv writer
            writer = csv.writer(csvfile)

            # write a row to the csv file
            writer.writerow([])
