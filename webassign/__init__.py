
import sys
import csv
import traceback
from cStringIO import StringIO
from pprint import pprint
from itertools import izip
from copy import copy
from dateutil import parser as date_parser

from csvu import default_arg_parser, writer_make

class WADialect(csv.Dialect):
    doublequote = False
    escapechar = '\\'
    delimiter = '\t'
    quotechar = '"'
    skipinitialspace = True
    lineterminator = '\r\n'
    quoting = csv.QUOTE_MINIMAL

WA_USERNAME_DEFAULT = 'webassign_username'

def webassign_parser_d(f):

    # Course/file information
    coursename = f.readline().strip()
    instructor = f.readline().strip()
    created0   = f.readline().strip()
    created    = date_parser.parse(created0).isoformat()

    # Blank line
    f.readline() 

    ##
    ## The next several lines are information
    ## about the assignments. Read these lines
    ## into an in-memory file and read it as CSV.
    ##
    header = StringIO()
    header.write(f.readline())
    header.write(f.readline())
    header.write(f.readline())
    header.seek(0)

    # Blank line
    f.readline()

    h_reader = csv.reader(header, dialect=WADialect())
    h_rows   = [row for row in h_reader]

    i_h_total = 2
    try:
        i_h_total = h_rows[0].index('Total')
    except ValueError:
        pass

    # Clip blank columns
    h_rows = [row[i_h_total:] for row in h_rows]

    assignments = [{'name': col[0], 'due': date_parser.parse(col[1]).isoformat(), 'total': col[2]} for col in izip(*h_rows)]

    ##
    ## The rest of the file is the scores.
    ##
    f_reader = csv.reader(f, dialect = WADialect())

    f_meta = f_reader.next()
    f_meta = f_meta[:i_h_total]
    f_meta.extend(ass['name'] for ass in assignments) # haha
    
    def generator():
        for row in f_reader:
            yield dict(izip(f_meta, row))

    return {
                'coursename' : coursename,
                'instructor' : instructor,
                'created'    : created,
                'assignments': assignments,
                'fieldnames' : f_meta,
                'generator'  : generator()
            }


def to_meta_arg_parser():
    description = 'WebAssign to Meta takes a WebAssign Report produces the meta information.'
    parser = default_arg_parser(
                    description=description,
                )
    parser.add_argument(
            '--file0', 
            type=str, 
            default='-',
            help='Input WebAssign report file, defaults to STDIN.'
        )
    return parser

def to_meta_program():

    parser = to_meta_arg_parser()

    args = parser.parse_args()

    try:
        file0 = sys.stdin

        if args.file0 != '-':
            file0 = open(args.file0, 'r')

        parser_d = webassign_parser_d(file0)

        del parser_d['generator']
        del parser_d['fieldnames']

        pprint(parser_d)

    except Exception as exc:

        m = traceback.format_exc()
        parser.error(m)
        
def to_csv_arg_parser():
    description = 'WebAssign to CSV takes a WebAssign Report produces a CSV of the scores.'
    parser = default_arg_parser(
                    description=description,
                    file1='output',
                )
    parser.add_argument(
            '--file0', 
            type=str, 
            default='-',
            help='Input WebAssign report file, defaults to STDIN.'
        )
    parser.add_argument(
            '--dialect1', 
            default='excel', 
            choices=['excel', 'excel-tab', 'pretty',],
            help='''The CSV dialect of the output.
                    Option *excel* dialect uses commas, 
                    *excel-tab* uses tabs,
                    *pretty* prints a human-readable table.
                    '''
        )
    parser.add_argument(
            '--absolute',
            default=False, 
            action='store_true', 
            help='''Print the absolute scores instead of percentages.'''
        )
    parser.add_argument(
            '--keeptotal',
            default=False, 
            action='store_true', 
            help='''Print the Total column instead of omitting it.'''
        )
    parser.add_argument(
            '--keyname',
            default='Username', 
            type=str,
            help='''The name of column to use as the key.'''
        )
    parser.add_argument(
            '--rename',
            default=WA_USERNAME_DEFAULT, 
            type=str,
            help='''The name to rename the key column to.'''
        )
    return parser

def to_csv_g(parser_d, absolute=False, keeptotal=False, keyname='Username', rename=WA_USERNAME_DEFAULT):

    assignments = parser_d['assignments']

    if not keeptotal:
        assignments = [ass for ass in assignments if ass['name'] != 'Total']

    fieldnames = [keyname]
    fieldnames.extend(ass['name'] for ass in assignments)

    def g_abs():
        for row in parser_d['generator']:
            yield {fn: row[fn] for fn in fieldnames}

    def g_pct():

        totals = dict((ass['name'], float(ass['total'])) for ass in assignments)

        def pct(v, fn):
            try:
                w = float(v)
                z =  w / totals[fn] * 100.0
                return z
            except:
                pass
            return v
        for row in parser_d['generator']:
            yield {fn: pct(row[fn], fn) for fn in fieldnames}

    g0 = g_abs
    if not absolute:
        g0 = g_pct

    g1 = g0
    if keyname == 'Username':
        def fixusername(row):
            u = row[keyname]
            k = u.find('@')
            row[keyname] = u[:k]
            return row
        def g_username():
            for row in g0():
                yield fixusername(row)
        g1 = g_username

    g2 = g1
    fieldnames1 = copy(fieldnames)
    if rename:
        fieldnames1[0] = rename
        def fixkeyname(row):
            u = row[keyname]
            del row[keyname]
            row[rename] = u
            return row
        def g_rename():
            for row in g1():
                yield fixkeyname(row)
        g2 = g_rename

    # FIXME: Fix column names?

    return {'fieldnames': fieldnames1, 'to_csv_g': g2()}
    
def to_csv_program():

    parser = to_csv_arg_parser()

    args = parser.parse_args()

    try:
        file0 = sys.stdin

        if args.file0 != '-':
            file0 = open(args.file0, 'r')

        parser_d = webassign_parser_d(file0)

        filter_d = to_csv_g(
                            parser_d=parser_d,
                            absolute=args.absolute,
                            keeptotal=args.keeptotal,
                            keyname=args.keyname,
                            rename=args.rename,
                        )

        filter_g    = filter_d['to_csv_g']
        fieldnames1 = filter_d['fieldnames']
        
        writer_f = writer_make(
                        fname=args.file1,
                        dialect=args.dialect1,
                        fieldnames=fieldnames1,
                        headless=False,
                    )

        writer_f(filter_g)

    except Exception as exc:

        m = traceback.format_exc()
        parser.error(m)
        

