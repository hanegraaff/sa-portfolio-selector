import unittest
from unittest.mock import patch
from intrinio_sdk.rest import ApiException
from exception.exceptions import ValidationError, DataError
from data_provider import intrinio_data
from  support.financial_cache import cache
from test import nop
import datetime


class TestDataProviderIntrinioData(unittest.TestCase):

    '''
        Financial Metric tests
    '''
    
    def test_read_financial_metric_with_api_exception(self):
        with patch.object(intrinio_data.company_api, 'get_company_historical_data', \
                    side_effect=ApiException("Server Error")), \
             patch('support.financial_cache.cache', new=nop.Nop()):

            with self.assertRaises(DataError):
                intrinio_data.__read_financial_metric__('NON-EXISTENT-TICKER', 2018, 'tag')

    def test_read_financial_metric_with_invalid_year(self):
        with self.assertRaises(ValidationError):
            intrinio_data.__read_financial_metric__('AAPL', 0, 'tag')

        with self.assertRaises(ValidationError):
            intrinio_data.__read_financial_metric__('AAPL', 0, 'tag')


    '''
        __read_company_data_point__
    '''
    def test_read_financial_metric_with_api_exception(self):
        with patch.object(intrinio_data.company_api, 'get_company_data_point_number', \
                    side_effect=ApiException("Server Error")), \
             patch('support.financial_cache.cache', new=nop.Nop()):

            with self.assertRaises(DataError):
                intrinio_data.__read_company_data_point__('NON-EXISTENT-TICKER', 'tag')


    '''
        Financial statement tests
    '''
    def test_historical_cashflow_stmt_with_api_exception(self):
        with patch.object(intrinio_data.fundamentals_api, 'get_fundamental_standardized_financials',
                          side_effect=ApiException("Not Found")), \
             patch('support.financial_cache.cache', new=nop.Nop()):
            with self.assertRaises(DataError):
                intrinio_data.get_historical_cashflow_stmt('NON-EXISTENT-TICKER', 2018, 2018, None) 

    def test_historical_income_stmt_with_api_exception(self):
        with patch.object(intrinio_data.fundamentals_api, 'get_fundamental_standardized_financials',
                          side_effect=ApiException("Not Found")), \
             patch('support.financial_cache.cache', new=nop.Nop()):
            with self.assertRaises(DataError):
                intrinio_data.get_historical_income_stmt('NON-EXISTENT-TICKER', 2018, 2018, None) 

    def test_historical_balacesheet_stmt_with_api_exception(self):
        with patch.object(intrinio_data.fundamentals_api, 'get_fundamental_standardized_financials',
                          side_effect=ApiException("Not Found")), \
             patch('support.financial_cache.cache', new=nop.Nop()):
            with self.assertRaises(DataError):
                intrinio_data.get_historical_balance_sheet('NON-EXISTENT-TICKER', 2018, 2018, None) 

    '''
        Stock Price Tests
    '''
    def test_daily_stock_prices_with_api_exception(self):
        with patch.object(intrinio_data.security_api, 'get_security_stock_prices',
                        side_effect=ApiException("Not Found")), \
             patch('support.financial_cache.cache', new=nop.Nop()):
            with self.assertRaises(DataError):
                intrinio_data.get_daily_stock_close_prices('NON-EXISTENT-TICKER', datetime.date(2018, 1, 1), datetime.date(2019, 1, 1)) 

    def test_daily_stock_prices_with_other_exception(self):
        with patch.object(intrinio_data.security_api, 'get_security_stock_prices',
                        side_effect=KeyError("xxx")), \
             patch('support.financial_cache.cache', new=nop.Nop()):
            with self.assertRaises(ValidationError):
                intrinio_data.get_daily_stock_close_prices('NON-EXISTENT-TICKER', datetime.date(2018, 1, 1), datetime.date(2019, 1, 1)) 
