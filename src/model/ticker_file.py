from support import constants
from support import util
from exception.exceptions import AWSError, FileSystemError, ValidationError
from cloud import aws_service_wrapper
import logging
import os

log = logging.getLogger()

class TickerFile():
    '''
        A Class that models a Ticker File.
        Ticker Files reresent the universe of stocks that the recommendation
        system will analyze and rank.

        They are simple text files containing a single stock per file.
        E.g.
            AAPL
            MSFT
            GE
            ...

        This class can be initialized using a local ticker file or by downloading
        one from S3

        Attributes
        ----------
        ticker_list : list
            The list of ticker symbols extracted from the file

    '''
    

    def __init__(self, ticker_list : list):
        self._ticker_list = ticker_list


    @classmethod
    def from_local_file(cls, ticker_path: str, ticker_file_name : str):
        '''
            Creates a TickerFile object instance from a local file

            Parameters
            ----------
            ticker_path : str
                path of the ticker file
    
            ticker_file_name : str
                name of the ticker file
        '''
        try:
            destination_path = "%s/%s" % (ticker_path, ticker_file_name)

            log.debug("Reading Ticker File: %s" % destination_path)
            with open(destination_path) as f:
                ticker_list = f.read().splitlines()
            return cls(ticker_list)
        except Exception as e:
            raise FileSystemError("Could not read ticker file", e)

    @classmethod
    def from_s3_bucket(cls, ticker_object_name : str, app_ns : str):
        '''
            Creates a TickerFile object instane based on an S3 bucket.
            The bucket is detrmined by looking at the system's ClouFormation 
            exports.

            Parameters
            ----------
            ticker_object_name : str
                S3 object bane
            app_ns : str
                Application namespace used to identify the appropriate
                CloudFormation exports

        '''
        s3_object_path = "%s/%s" % (constants.s3_ticker_file_folder_prefix, ticker_object_name)
        destination_path = "%s/%s" % (constants.app_data_dir, ticker_object_name)

        filter_list = constants.app_cf_stack_names

        log.debug("Reading S3 Data Bucket location from CloudFormation Exports")
        app_cf_exports = aws_service_wrapper.cf_list_exports(filter_list)
        s3_data_export_name = constants.s3_data_bucket_export_name(app_ns)

        try:    
            s3_data_bucket_name = app_cf_exports[s3_data_export_name]
        except Exception:
            raise ValidationError("%s could not be found in clouformation exports." % s3_data_export_name, None)

        util.create_dir(constants.app_data_dir)
        log.debug("Downloading s3://%s --> %s" % (s3_object_path, destination_path))
        
        try:
            aws_service_wrapper.s3_download_object(s3_data_bucket_name, s3_object_path, destination_path)
        except AWSError as awe:
            if "(404)" in str(awe) and "Not Found" in str(awe):
                log.debug("File not found in S3. Looking for local alternatives")

                # Attempt to upload a local copy of the file if it exists
                local_ticker_path  = '%s/%s' % (constants.ticker_data_dir, ticker_object_name)

                if os.path.isfile(local_ticker_path):
                    log.debug("Attempting to upload %s --> s3://%s/%s" % (local_ticker_path, s3_data_bucket_name, s3_object_path))
                    aws_service_wrapper.s3_upload_object(local_ticker_path, s3_data_bucket_name, s3_object_path)

                    return cls.from_local_file(constants.ticker_data_dir, ticker_object_name)
                else:
                    log.debug("No local alternatives found")
                    raise awe
            else:
                raise awe

        return cls.from_local_file(constants.app_data_dir, ticker_object_name)
    

    
    @property
    def ticker_list(self):
        '''
            ticker list getter
        '''
        return self._ticker_list