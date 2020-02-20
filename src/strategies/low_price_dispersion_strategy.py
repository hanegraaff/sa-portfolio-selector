import pandas as pd
from datetime import datetime
from data_provider import intrinio_data, intrinio_util
import logging
from support import util
from strategies.portfolio import Portfolio
from exception.exceptions import BaseError, ValidationError, DataError



class LowPriceDispersionStrategy():
    """
        An invenstment strategy based on analyst targer price agreement measured as
        the price dispersion, as detailed in this paper:

        https://www8.gsb.columbia.edu/faculty-research/sites/faculty-research/files/FRANK%20ZHANG%20PAPER%20PSZ_20190913.pdf

        Specifically, given a list ticker symbols, it will return a portfolio recommendation
        based on the supplied list that consists of stocks with the lowest price dispersion (highest analyst agreement)
        and highest price target.

        The portfolio is represented as a JSON document like this:

        {
            'portfolio_name': str
            'creation_time': iso8601 date
            'data_date': iso8601 date
            'portfolio':[
                'str', 'str', 'str'
            ]
        }

        Note that for this strategy to be most effective you must supply a large set of tiker
        symbols.


    """

    STRATEGY_NAME = "LOW_PRICE_DISPERSION"

    def __init__(self, ticker_list : list, year : int, month : int, portfolio_size : int):
        """
            Initializes the class with the ticker list, a year and a month.

            The year and month are used to set the context of the analysis,
            meaning that financial data will be used for that year/month. 
            This is done to allow the analysis to be run in the past and test the
            quality of the results.


            Parameters
            ------------
            ticker_list : list of tickers to be included in the analisys
            year : analysis year
            month : analysis month
            portfolio_size : number of recommended stocks that will be returned
             by this strategy
            
            Returns
            ------------
            None
        """

        if (ticker_list is None or len(ticker_list) == 0):
            raise ValidationError("No ticker list was supplied", None)

        if  len(ticker_list) < 2:
            raise ValidationError("You must supply at least 2 ticker symbols", None)

        (self.data_start_date, self.data_end_date) = intrinio_util.get_month_date_range(year, month)

        self.ticker_list = ticker_list
        self.today = datetime.now()

        self.portfolio_size = portfolio_size

    def __load_financial_data__(self):
        """
            loads financial data into a map that is suitable to be converted
            into a pandas data frame

            pricing_raw_data = {
                'ticker': [],
                'target_price_avg': [],
                'target_price_sdtdev': [],
                'target_price_sdtdev_pct': []
            }

            
            Raises
            ------------
            DataError in case financial data could not be loaed for any
            securities

            Parameters
            ------------
            None
            
            Returns
            ------------
            None

        """

        pricing_raw_data = {
            'ticker': [],
            'analysis_price': [],
            'target_price_avg': [],
            'current_price': [],
            'target_price_sdtdev_pct': [],
            'analyst_expected_return': [],
            'actual_return': []
        }
    
        dds = self.data_start_date
        dde = self.today if (self.today < self.data_end_date) else self.data_end_date
        year = dds.year
        month = dds.month

        at_least_one = False

        for ticker in self.ticker_list:
            try:
                target_price_sdtdev = intrinio_data.get_target_price_std_dev(ticker, dds, dde)[year][month]
                target_price_avg = intrinio_data.get_target_price_mean(ticker, dds, dde)[year][month]
                target_price_sdtdev_pct = target_price_sdtdev / target_price_avg * 100

                analysis_price = intrinio_data.get_latest_close_price(ticker, dde, 5)
                current_price = intrinio_data.get_latest_close_price(ticker, self.today, 5)

                analyst_expected_return = self.__calc_return_factor__(analysis_price, target_price_avg)
                actual_return = self.__calc_return_factor__(analysis_price, current_price)
                
                pricing_raw_data['ticker'].append(ticker)
                pricing_raw_data['analysis_price'].append(analysis_price)
                pricing_raw_data['target_price_avg'].append(target_price_avg)
                pricing_raw_data['current_price'].append(current_price)
                pricing_raw_data['target_price_sdtdev_pct'].append(target_price_sdtdev_pct)
                pricing_raw_data['analyst_expected_return'].append(analyst_expected_return )
                pricing_raw_data['actual_return'].append(actual_return)

                at_least_one = True
            except BaseError as be:
                logging.debug("Could not read %s financial data, because: %s" % (ticker, str(be)))
            except Exception as e:
                raise DataError("Could not read %s financial data" % (ticker), e)

        if not at_least_one:
            raise DataError("Could not load pricing data for any if the supplied tickers", None)
        
        return pricing_raw_data


    def __calc_return_factor__(self, price_from : float, price_to : float):
        """
            calculates the return as a factor give two prices
        """
        return (price_to - price_from) / price_from

        

    def __convert_to_data_frame__(self, pricing_raw_data : dict):
        """
            converts the supplied financial_data into a pandas data frame.

            Parameters
            ------------
            ticker_list : list of tickers to be included in the analisys
            
            Returns
            ------------
            None
        """
        raw_dataframe = pd.DataFrame(pricing_raw_data).set_index('ticker')
        raw_dataframe['decile'] = pd.qcut(pricing_raw_data['target_price_sdtdev_pct'], 10, labels=False, duplicates='drop')
        raw_dataframe =  raw_dataframe.sort_values(['decile', 'analyst_expected_return'], ascending = (True, False))
    
        selected_portfolio = raw_dataframe.head(self.portfolio_size).drop(['decile', 'target_price_avg', 'target_price_sdtdev_pct', 'analyst_expected_return'], axis=1)

        return (selected_portfolio, raw_dataframe)

    def generate_portfolio(self):
        """
            Creates a recommended portfolio and returns it as a pandas data frame
            and with the following fields:

            'ticker',
            'analysis_price',
            'current_price',
            'actual_return'

            Parameters
            ------------
            None

            Raises
            ------------
            DataError in case financial data could not be loaed for any
            securities
            
            Returns
            ------------
            A pandas data frame containing the recommended portfolio
        """
        (self.portfolio_dataframe, self.raw_dataframe) = self.__convert_to_data_frame__(self.__load_financial_data__())

        p = Portfolio(self.today, self.data_end_date, self.STRATEGY_NAME, self.portfolio_dataframe.index.values.tolist())
        
        return p