# kompare
Python CLI to compare documents in elasticsearch and dynamodb and identify the difference

## Installation
```bash
$ git clone https://github.com/radiantone/kompare
$ cd kompare
$ make install
$ source venv/bin/activate
```
## Overview
`kompare` is a CLI tool for comparing synchronization between elasticsearch indices and dynamodb tables in either direction depending on which is your source of truth (usually it will be dynamodb).

## Configuration

```bash
$ more kompare.ini 
[elasticsearch]
url=https://elastic:PASSWORD@localhost:9200

[dynamodb]
url=http://localhost:8009

```
## Usage

```bash
(venv) $ kompare
Usage: kompare [OPTIONS] COMMAND [ARGS]...

Options:
  --debug  Debug switch
  --help   Show this message and exit.

Commands:
  dyn2es   Scan dynamodb and find matches in elasticsearch
  es2dyn   Scan elasticsearch and find matches in dynamodb
  indices  List elasticsearch indices
  tables   List dynamodb tables

(venv) $ kompare es2dyn -eid id -did id -i test-index -t test
Scanning |################################| 3/3
+--------------+------------+----------------+---------------+--------+-------+
| Dynamo Table |  ES Field  | DynamoDB Field | Elastic Index | Misses | Total |
+--------------+------------+----------------+---------------+--------+-------+
|     test     | test-index |       id       |       id      |   2    |   3   |
+--------------+------------+----------------+---------------+--------+-------+

(venv) $ kompare dyn2es -eid id -did id -i test-index -t test
Scanning |################################| 1/1
+--------------+------------+----------------+---------------+--------+-------+
| Dynamo Table |  ES Field  | DynamoDB Field | Elastic Index | Misses | Total |
+--------------+------------+----------------+---------------+--------+-------+
|     test     | test-index |       id       |       id      |   0    |   1   |
+--------------+------------+----------------+---------------+--------+-------+

```
