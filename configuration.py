from decimal import Decimal as D

tcmb_today_url='http://www.tcmb.gov.tr/kurlar/today.xml'
tcmb_archive_url='http://www.tcmb.gov.tr/kurlar/%Y%m/%d%m%Y.xml'
local_cache='/tmp/'
cache_file='tcmb_today%s.xml'

standard_codes = {'TL': 'TRY',
                  'TRL': 'TRY',
                  'YTL': 'TRY'}

builtin_rates = {'TRY': D('1.0')}
