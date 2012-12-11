import urllib
from xml.dom import minidom
from os.path import join
import datetime
from decimal import Decimal as D, ROUND_HALF_EVEN, InvalidOperation

from configuration import builtin_rates
import configuration as config
from language import turkish as message


'''
Module that downloads currency data from TCMB (Central Bank of Turkey).

TCMB has some idiosyncracies:
1. Each day, the valid rates are published at around 15:30.
   Before that, the previous day's rates are available.
2. New rates are not announced on weekends or holidays.
3. The page config.tcmb_today_url returns the most recent
   published rates, even if "today" is a holiday.
4. Archived dates' rates are stored in a different location:
   config.tcmb_archive_url.
5. Dates on which rates were not published (or are not available)
   return 404 on the archive url.
'''

earliest_date = datetime.date(1996, 4, 16)    

def daystamp(date=None):
    if date is None:
        return datetime.datetime.now().strftime('%d%m%Y')
    else:
        return date.strftime('%d%m%Y')

def clean_cache():
    # delete files that are earlier than today.
    # if cache is kept in /tmp, no need to do this.
    pass

def load_tcmb(date=None):
    # date == None means try to load today's rates.
    if date is None:
        return load_tcmb_today()
    # Check if the given date is sensical.
    if date > datetime.datetime.today().date():
        # A date in the future? Surely today's rates apply.
        return load_tcmb_today()
    if date < earliest_date:
        raise RuntimeError("TCMB only provides rated for dates after April 16, 1996.")
    
    for_date = date
    if date.isoweekday() in (6, 7):
        # A weekend. Try to read the previous Friday.
        for_date -= datetime.timedelta(date.isoweekday() - 5)
    # Try to download the date's data from tcmb. If can't find (get 404),
    # successively try to get earlier dates.
    while True:
        ret = load_tcmb_archive(for_date)
        if ret is not None:
            dom, for_date = ret
            if config.verbose and for_date < date:
                print message['not_published']
                print message['using_rates_from'] % for_date.strftime(message['date'])
            return dom, for_date
        for_date -= datetime.timedelta(-1)

def load_tcmb_archive(for_date):
    try:
        if config.verbose:
            print 'Trying to read from cache: %s' % join(config.local_cache, config.cache_file % daystamp(for_date))
        f = open(join(config.local_cache, config.cache_file % daystamp(for_date)))
        return minidom.parse(f), for_date
    except IOError:
        if config.verbose:
            print 'Trying to read from url: %s' % for_date.strftime(config.tcmb_archive_url)
        f = urllib.urlopen(for_date.strftime(config.tcmb_archive_url))
        if f.getcode() != 200:
            # Can't get the file.
            return None
        dom = minidom.parse(f)
        date_str = dom.getElementsByTagName('Tarih_Date')[0] \
                   .getAttribute('Tarih').replace('.', '')
        date = datetime.datetime.strptime(date_str, '%d%m%Y').date()
        if config.verbose:
            print 'Writing to cache: %s' % join(config.local_cache, config.cache_file % date_str)
        f = open(join(config.local_cache, config.cache_file % date_str), 'w')
        f.write(dom.toxml('utf-8'))
        f.close()
        return dom, date

def load_tcmb_today():
    try:
        if config.verbose:
            print 'Trying to read from cache: %s' % join(config.local_cache, config.cache_file % daystamp())
        f = open(join(config.local_cache, config.cache_file % daystamp()))
        return minidom.parse(f), datetime.datetime.today().date()
    except IOError:
        if config.verbose:
            print 'Trying to read from url: %s' % config.tcmb_today_url
        f = urllib.urlopen(config.tcmb_today_url)
        dom = minidom.parse(f)
        date_str = dom.getElementsByTagName('Tarih_Date')[0] \
                   .getAttribute('Tarih').replace('.', '')
        date = datetime.datetime.strptime(date_str, '%d%m%Y')
        if config.verbose and date.date() < datetime.datetime.today().date():
            print message['not_published']
            print message['using_rates_from'] % date.strftime(message['date'])
        if config.verbose:
            print 'Writing to cache: %s' % join(config.local_cache, config.cache_file % date_str)
        f = open(join(config.local_cache, config.cache_file % date_str), 'w')
        f.write(dom.toxml('utf-8'))
        f.close()
        return dom, date

def get_float(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    try:
        return D(''.join(rc))
    except (ValueError, InvalidOperation):
        return None

def get_rates(from_, to_, conversion, for_date):
    clean_cache()
    dom, date = load_tcmb(for_date)

    from_rate, to_rate = None, None
    for curr in dom.getElementsByTagName('Currency'):
        try:
            curr_rate = get_float(curr.getElementsByTagName(conversion)[0].childNodes)
        except IndexError:
            continue
        if curr_rate is None:
            continue
        if curr.getAttribute('CurrencyCode').lower() == from_.lower():
            from_rate = curr_rate
        if curr.getAttribute('CurrencyCode').lower() == to_.lower():
            to_rate = curr_rate

    if from_rate is None:
        from_rate = builtin_rates.get(from_, D('1.0'))
    if to_rate is None:
        to_rate = builtin_rates.get(to_, D('1.0'))

    return (from_rate, to_rate, date)
