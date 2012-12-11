#! /usr/bin/python
import urllib
from xml.dom import minidom
import configuration as config
from os.path import join
import datetime
import sys, getopt
from decimal import Decimal as D, ROUND_HALF_EVEN, InvalidOperation
from language import turkish as message
from tcmb import get_rates as tcmb_rates

config.verbose = False

def usage():
    return '''
Usage: ./currency.py [OPTION] [AMOUNT] [FROM_CURRENCY] [TO_CURRENCY]
Calculate currency rates according to TCMB published rates.

Cross-rates are calculated through TL.

Parameters

-r --reverse    Reverse conversion.
-t --type       Conversion type. Default: banknote_sell
                forex_sell, fs, ForexSelling: Forex sell rate
                forex_buy, fb, ForexBuying: Forex buy rate
                banknote_sell, bs, s, BanknoteSelling: Banknote ('efektif') sell rate
                banknote_buy, bb, b, BanknoteBuying: Banknote ('efektif') buy rate
-s --succint    Succint output: returns only the amount.
-p --precision  Set the precision of output. Default: 2.
-d --date       Get currency for date (default is today).
                Date should be defined as in 210712, meaning July 21, 2012.
-v --verbose    Verbose mode.

Examples

# ./currency.py 10 USD
10.00 USD -> 18.21 TRL (BanknoteSelling)

# ./currency.py 10 USD TRL
10.00 USD -> 18.21 TRL (BanknoteSelling)

# ./currency.py -r 10 USD
10.00 TRL -> 8.11 USD (BanknoteSelling)

# ./currency.py -r 10 USD TRL
10.00 TRL -> 8.11 USD (BanknoteSelling)

# ./currency.py -t fb 10 USD
10.00 USD -> 18.25 TRL (ForexBuying)

# ./currency.py 10 GBP USD
10.00 GBP -> 18.21 USD (BanknoteSelling)
'''

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg
        
conversion_dict = {'forex_sell': 'ForexSelling',
                   'fs': 'ForexSelling',
                   'forex_buy': 'ForexBuying',
                   'fb': 'ForexBuying',
                   'banknote_buy': 'BanknoteBuying',
                   'banknote_sell': 'BanknoteSelling',
                   'b': 'BanknoteBuying',
                   's': 'BanknoteSelling',
                   'bb': 'BanknoteBuying',
                   'bs': 'BanknoteSelling',
                   None: 'BanknoteSelling',
                   }

def quantize(dec, scale):
    return dec.quantize(D('1').scaleb(-scale), rounding=ROUND_HALF_EVEN)

def main_(from_, to_, conversion, amount,
          scale=2, succint=False, for_date=None):
    if for_date is None:
        for_date = datetime.datetime.today().date()
    from_ = config.standard_codes.get(from_, from_)
    to_ = config.standard_codes.get(to_, to_)
    conversion = conversion_dict.get(conversion, conversion)

    from_rate, to_rate, date = tcmb_rates(from_, to_, conversion, for_date)

    rate = from_rate / to_rate
    amount = D(amount)
    result = amount * rate
    result = quantize(result, scale)
    rate = quantize(rate, scale)
    amount = quantize(amount, scale)

    if succint:
        print '%.2f' % result
    else:
        print '%s %s -> %s %s' % (amount,
                                  from_,
                                  result,
                                  to_,
                                  )
        print message['Rate_'] % (rate,
                                  conversion,
                                  )
        print message['tcmb_published_rate'] % date.strftime('%d %B %Y')
    return (result, from_, to_, rate, conversion)

def test():
    from_ = 'GBP'
    to_ = 'USD'
    amount = 10.0
    conversion = 'bs'
    main_(from_, to_, conversion, amount)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    try:
        try:
            opts, args = getopt.getopt(argv[1:], 'hrt:sp:d:v',
                                       ['help', 'reverse', 'type',
                                        'succint', 'precision', 'date',
                                        'verbose',
                                        ])

        except getopt.error, msg:
            raise Usage(msg)

        conversion = 'bs'
        reverse = False
        succint = False
        scale = 2
        date = None
        for (o, a) in opts:
            if o in ("-h", "--help"):
                print usage()
                return 2
            elif o in ("-r", "--reverse"):
                reverse = True
            elif o in ('-t', '--type'):
                conversion = a
            elif o in ('-s', '--succint'):
                succint = True
            elif o in ('-p', '--precision'):
                scale = int(a)
            elif o in ('-d', '--date'):
                date = datetime.datetime.strptime(a, '%d%m%y').date()
            elif o in ('-v', '--verbose'):
                config.verbose = True
        
        if len(args) < 2:
            raise Usage('Need at least the amount and currency to convert to.')

        amount = args[0]
        from_curr = args[1]
        if len(args) > 2:
            to_curr = args[2]
        else:
            to_curr = 'TRL'

        if reverse:
            from_curr, to_curr = to_curr, from_curr

        if config.verbose:
            print 'Will convert %s %s to %s (conversion: %s), with a precision of %d digits.' % (amount, from_curr, to_curr,
                                                                                                 conversion, scale)
            print 'Output is %sverbose, and is %ssuccint.' % ('' if config.verbose else 'not ',
                                                              '' if succint else 'not ')

        main_(from_curr, to_curr, conversion, amount, scale=scale, succint=succint, for_date=date)
        
        return 0
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "TCMB currency converter"
        print >>sys.stderr, "Usage:   ./currency.py [OPTION] [AMOUNT] [FROM_CURRENCY] [TO_CURRENCY]"
        print >>sys.stderr, "Example: ./currency.py 10 USD TL"
        print >>sys.stderr, "For help use --help"
        return 2

if __name__ == '__main__':
    sys.exit(main())
