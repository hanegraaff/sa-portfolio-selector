# Overview
![Stock Advisor Design](doc/stock-advisor-services.png)

This repo is part of the Stock Advisor project found here:

https://github.com/hanegraaff/stock-advisor-main-project

This project covers the application software that constitutes the Stock Advisor System, namely the Securities Recommendation Service and the Portfolio Manager.


# Table of Contents
* [Financial Data](#financial-data)
* [Prerequisites](#prerequisites)
    * [API Keys](#api-keys)
    * [Develpment Environment](#develpment-environment)
* [Securities Recommendation Service](#securities-recommendation-service)
    * [Release Notes](#recommendation-service-release-notes)
    * [Algorithm Description](#algorithm-description)
    * [Running the service from the command line](#running-the-service-from-the-command-line)
        * [Production mode](#production-mode)
        * [Test mode](#test-mode)
    * [Output](#recommendation-service-output)
    * [Caching of financial data](#caching-of-financial-data)
    * [Backtesting](#backtesting)
* [Portfolio Manager](#portfolio-manager)
    * [Release Notes](#portfolio-manager-release-notes)
    * [Trading Strategy](#trading-strategy)
    * [Running the service from the command line](#running-the-portfolio-manager-from-the-command-line)
    * [Output](#portfolio-manager-output)
* [Running the services](#running-the-services)
    * [Running the service as a docker image](#running-the-service-as-a-docker-image)
    * [Running the service in ECS](#running-the-service-in-ECS)
* [Unit Testing](#unit-testing)

# Financial Data
This software relies on financial data to perform its calculations, specifically it requires current and historical pricing information as well as analyst target price predictions. This data is sourced from Intrinio, though other providers could be used.

Intrinio offers free access to their sandbox, which gives developers access to a limited dataset comprising of the DOW30, and the results presented here are based on that list. A paid subscription allows access to a much larger universe of stocks.

# Prerequisites
1) Python 3.8 (required for latest argparse features)
2) Intrinio API Key
3) Access to AWS account with properly configured AWS Keys.
4) Ability to interact with AWS Services using the console, specifically ECS, ECR, S3, SNS, Parameter Store and CodeBuild.

## API Keys
An API Key for the Intrinio (https://www.intrinio.com) with access to the "US Fundamentals and Stock Prices" and "Zacks Price Targets" feeds

the API must be saved to the environment like so:

```export INTRINIO_API_KEY=[your API key]```

## Develpment Environment
```pip install -r requirements.txt```

It is highly recommended to run this in a virtual environment:

```
python3 -m venv venv
source venv/bin/activate

cd src
pip install -r requirements.txt
```
Be sure that ```python3``` points to Python 3.8. Alternatively you can create the virtual environment this way:

```
python3.8 -m venv venv
...
```

All scripts must be executed from the ```src``` folder.


# Securities Recommendation Service
![Security Recommendation Service Design](doc/recommendation-service.png)

The Securities Recommendation service is a component of the Stock Advisor system that generates monthly US Equities recommendations using a market sentiment algorithm that ranks stocks the level of analyst target price agreement. It is based on the findings of paper like these:

|Paper|Author(s)|
|--|--|
|[Consensus Analyst Target Prices: Information Content and Implications for Investors](doc/Consensus-Analyst-Target-Prices.pdf)|Asa B. Palley, Thomas D. Steffen, X. Frank Zhang|
|[Dispersion in Analysts’ Target Prices and Stock Returns](doc/Dispersion-Analysts-Target-Prices-Stock-Returns.pdf)|Hongrui Feng Shu Yan|
|[The predictive power of analyst price target and its dispersion](doc/Predictive-Power-Analyst-Price-Target-Dispersion.pdf)|Heng(Emily) Wang, Shu Yan|

They suggest, among other things, that when taken individually or even on average, analyst price targets are not a good predictor of returns, but the degree of agreement/disagreement is.


## Recommendation Service Release Notes
This is an initial version that offers the following features

* Ability to rank securities and generate recommendation.
* Local caching of financial data
* Back testing capability
* Ability to run inside a Docker container
* Integrate into Stock Advisor Infrastructure, specifically ECS.

## Algorithm Description
The algorithm reads a list of ticker symbols and downloads various financial data points. It then ranks each security into deciles, with the lowest decile containing stocks with the highest level of analyst price agreement and the highest decile containing stocks with the lowest price agreement. It then sorts each decile by expected returns, and returns a subset of the list. The number of securities that are returned are specified in the command using the ```-output-size``` option.

These are the specific steps:

1) Download financial data for each symbol:
    - Current Price
    - Analyst price forecast average
    - Analyst price forecast standard deviation
    - Analyst price forecast count (i.e. total forecasts)
2) Normalize the standard deviation by converting it into a relative percentage.
3) Rank the portfolio by this percentage and sort into deciles.
4) Select a subset from the last decile. This will return stocks with the largest level of disagreement.

## Running the service from the command line
The easiest way to run this service is via the command line. This section describes how.

```
src >>python securities_recommendation_svc.py -h
usage: securities_recommendation_svc.py [-h] -ticker_file TICKER_FILE -output_size
                                   OUTPUT_SIZE
                                   {test,production} ...

Reads a list of US Equity ticker symbols and recommends a subset of them based
on the degree of analyst target price agreement, specifically it will select
stocks with the lowest agreement and highest predicted return. The input
parameters consist of a file with a list of of ticker symbols, and the month
and year period for the recommendations. The output is a JSON data structure
with the final selection. When running this script in "production" mode, the
analysis period is determined at runtime, and the system will interact with the AWS
infrastructure to read inputs and store outputs.

optional arguments:
  -h, --help            show this help message and exit
  -ticker_file TICKER_FILE
                        Ticker Symbol local file path
  -output_size OUTPUT_SIZE
                        Number of selected securities

environment:
  runtime environment

  {test,production}     the runtime environment of the application. It can be
                        either "test" or "production"
    test                Test mode. Analysis period and current date must be
                        passed explicitly
    production          Production mode. Analysis period and current date are
                        determined at runtime
```

Where ```-ticker_file``` represents a local file or s3 object used to represent the universe of stocks that will be considered. It must contain
a single ticker symbol per line.

```
AAPL
AXP
BA
CAT
CSCO
CVX
...
```

and ```-output_size``` represents the total number of recommended
stocks resulting from the analysis.

The script can be run in two modes, representing different runtime environments.

### Production mode
**Production** mode will automatically determine the analysis period based on the calendar date, and display actual returns using the same. It will also use S3 to read the input ticker file and store results. This is the mode that must be used when running in ECS.

In this mode the service will identify the appropriate AWS infrastructure using a combination of CloudFormation exports and a namespace suppled to the command line (```-app_namespace```) used to avoid collisions. So for example, if the application namespace is set to ```sa```, the S3 bucket will be identified using the ```sa-data-bucket-name``` export. These are defined in the ```support.constants``` module.

```
src >>python securities_recommendation_svc.py production -h
usage: securities_recommendation_svc.py production [-h] -app_namespace
                                            APP_NAMESPACE

optional arguments:
-h, --help            show this help message and exit
-app_namespace APP_NAMESPACE
                        Application namespace used to identify AWS resources
```

For example:
```
python securities_recommendation_svc.py -ticker_file djia30.txt -output_size 3 production -app_namespace sa
```

This example generates a 3 stock recommendation using the DOW30 as an input, and using the latest analysis period based on calendar date.

### Test mode
**Test** mode expects the analysis period to be supplied using the command line, and will not interact with AWS, but rather rely on local resources. This mode is used when running and testing outside the production environment, and may also be used to run historically.

In this mode, ```-price_date``` is optional, and is used to determine the price date used to display the current returns of the selection.
    
```
src >>python securities_recommendation_svc.py test -h
usage: securities_recommendation_svc.py test [-h] -analysis_month ANALYSIS_MONTH
                                        -analysis_year ANALYSIS_YEAR
                                        [-price_date PRICE_DATE]

optional arguments:
  -h, --help            show this help message and exit
  -analysis_month ANALYSIS_MONTH
                        Analysis period's month
  -analysis_year ANALYSIS_YEAR
                        Analysis period's year
  -price_date PRICE_DATE
                        Price Date (YYYY/MM/DD) used to compute current
                        returns

```

For example:
```
python securities_recommendation_svc.py -ticker_file djia30.txt -output_size 3 test -analysis_year 2020 -analysis_month 1 -price_date 2020/03/01 
```

This will generate a 3 stock recommendation using a local ticker file of the DOW 30 using an analysis period of 01/2020 and a price date of 03/01

```analysis_year``` / ```analysis_month``` represent the financial period of the analyst forecasts, and ```price_date``` is the price date used to calculate the portfolio's current returns.


### Recommendation Service Output
The main output is a JSON Document with the portfolio recommendation.

```
[INFO] - 
[INFO] - Recommended Securities
[INFO] - {
    "set_id": "bda2de4e-7ec6-11ea-86e7-acbc329ef75f",
    "creation_date": "2020-04-15T03:11:03.841242+00:00",
    "analysis_start_date": "2020-03-01T00:00:00-05:00",
    "analysis_end_date": "2020-03-31T00:00:00-04:00",
    "price_date": "2020-03-31T00:00:00-04:00",
    "strategy_name": "PRICE_DISPERSION",
    "security_type": "US Equities",
    "securities_set": [
        {
            "ticker_symbol": "BA",
            "price": 152.28
        },
        {
            "ticker_symbol": "XOM",
            "price": 37.5
        },
        {
            "ticker_symbol": "GE",
            "price": 7.89
        }
    ]
```
Additionally, the program will display a Pandas Data Frame containing the ranked stocks used to select the final portfolio, and an indication of its relative performance compared to the average of all all supplied stocks.
```
[INFO] - 
[INFO] - Recommended Securities Return: 19.49%
[INFO] - Average Return: 4.77%
[INFO] - 
[INFO] - Analysis Period - 8/2019, Actual Returns as of: 2019/10/30
analysis_period ticker  dispersion_stdev_pct  analyst_expected_return  actual_return  decile
         2019-8     GE                30.652                    0.470          0.225       9
         2019-8   INTC                15.420                    0.136          0.194       9
         2019-8   AAPL                14.518                    0.063          0.165       9
         2019-8    UTX                13.414                    0.191          0.104       8
         2019-8    MMM                12.581                    0.116          0.041       8
         2019-8     PG                13.586                   -0.050          0.039       8
         2019-8    PFE                12.527                    0.246          0.082       7
         2019-8     GS                11.635                    0.223          0.058       7
         2019-8    CAT                10.072                    0.220          0.179       6
         2019-8     BA                 9.590                    0.184         -0.050       6
         2019-8   MSFT                10.812                    0.093          0.049       6
         2019-8    XOM                 8.444                    0.222         -0.011       5
         2019-8    NKE                 9.515                    0.102          0.067       5
         2019-8    UNH                 7.894                    0.248          0.089       4
         2019-8   CSCO                 8.093                    0.218          0.016       4
         2019-8    WMT                 8.045                   -0.007          0.034       4
         2019-8    IBM                 7.586                    0.157         -0.002       3
         2019-8    AXP                 7.826                    0.094         -0.019       3
         2019-8    MCD                 7.857                    0.021         -0.097       3
         2019-8    MRK                 7.522                    0.040         -0.003       2
         2019-8    TRV                 7.433                    0.038         -0.117       2
         2019-8    JPM                 7.262                    0.113          0.144       1
         2019-8     VZ                 6.668                    0.043          0.046       1
         2019-8     HD                 6.855                   -0.051          0.037       1
         2019-8    CVX                 5.515                    0.171         -0.012       0
         2019-8    JNJ                 5.205                    0.160          0.035       0
         2019-8      V                 5.398                    0.095         -0.009       0
```

When a new portfolio is generated a SNS event will be published resulting in the
below email.

```
From: sa-app-notification-topic (no-reply@sns.amazonaws.com)
To: Me

A New Stock Recommendation is available for the month of April


Ticker Symbol: BA
Ticker Symbol: GE
Ticker Symbol: XOM
```


Finally, when running in ```production``` mode, the service will also store results in S3

## Caching of financial data
All financial data is saved to a local cache to reduce throttling and API limits when using the Intrinio API. As of this version the data is set to never expire, and the cache will grow to a maximum size of 4GB.

The cache is located in the following path:

```
./financial-data/
./financial-data/cache.db
```

To delete or reset the contents of the cache, simply delete entire ```./financial-data/``` folder


## Backtesting
It is possible to backtest this strategy by running the price_dispersion_backtest.py script. It works by running the strategy from 05/2019 to 12/2019 and comparing the returns of the selected portfolio with the average of the list supplied to it.

Example:

```
>>python price_dispersion_backtest.py -ticker_file djia30.txt -output_size 3
[INFO] - Parameters:
[INFO] - Ticker File: djia30.txt
[INFO] - Output Size: 3

investment_period  ticker_sample_size  avg_ret_1M  sel_ret_1M  avg_ret_2M  sel_ret_2M  avg_ret_3M  sel_ret_3M
          2019/05                  12       8.09%       9.95%      11.17%      12.31%       8.74%       5.49%
          2019/06                  26       2.35%       3.56%      -2.00%     -10.78%       0.38%      -4.30%
          2019/07                  26      -3.10%     -11.72%      -1.03%      -5.64%      -0.07%      -3.24%
          2019/08                  26       2.78%       8.12%       4.55%      19.49%       7.09%      29.03%
          2019/09                  22       2.12%       9.60%       4.62%      17.53%       8.13%      21.29%
          2019/10                  27       2.65%       5.34%       5.01%       5.97%       6.43%      14.98%
          2019/11                  26       2.26%       0.68%       3.53%       8.88%      -8.55%      -7.02%
          2019/12                  25       1.46%       5.60%     -10.80%      -8.54%     -19.59%     -20.31%
investment_period ticker_sample_size  avg_tot_1M  sel_tot_1M  avg_tot_2M  sel_tot_2M  avg_tot_3M  sel_tot_3M
          ----/--                 --      18.59%      31.10%      15.05%      39.22%       2.56%      35.91%
```

Each line reports the returns for each montly portfolio selection at a 1 month, 2 month and 3 month horizon.

# Portfolio Manager
![Portfolio Manager Design](doc/portfolio-manager.png)

The Portfolio Manager service is a component of the Stock Advisor system that actively manager a protfolio based on the output of the recommendation service.

## Portfolio Manager Release Notes
This is software is still under development. It does not yet interact with an online broker and make trades.

* Create new portfolio based on latest recommendation or load existing one.
* Calculate the current returns
* Send SNS Notifications



## Trading Strategy
The initial version of the Portfolio Manager will take a random subset of the recommended securities and maintain a monthly portfolio of long positions. Over time this strategy will improve to allow for more frequent rebalancing.

* Read current recommendations from S3
* Create an empty portfolio and save it to S3

## Running the Portfolio Manager from the command line
```
>>python portfolio_manager_svc.py -h
usage: portfolio_manager_svc.py [-h] -app_namespace APP_NAMESPACE
                                -portfolio_size PORTFOLIO_SIZE

Executes trades and maintains a portfolio based on the output of the
recommendation service

optional arguments:
  -h, --help            show this help message and exit
  -app_namespace APP_NAMESPACE
                        Application namespace used to identify AWS resources
  -portfolio_size PORTFOLIO_SIZE
                        Number of securties that will be part of the portfolio
```

where ```app_namespace``` has the same maning as it does for the recommnedation service, namly to identify AWS resources based on the CloudFormation exports exposed by the infrastructure and automations scripts. ```portfolio_size``` on on the other hand will determine the size of the portfolio by selecting a subset of the recommendation.

For example:

```
>>python portfolio_manager_svc.py -app_namespace sa -portfolio_size 3
```

## Portfolio Manager Output

The main output of the service is an updated portfolio, stored in S3. Here is an example output generated by running the service

```
[INFO] - Application Parameters
[INFO] - -app_namespace: sa
[INFO] - -portfolio_size: 3
[INFO] - Loading latest recommendations
[INFO] - Downloading Security Recommendation Set: s3://app-infra-base-sadatabucketcc1b0cfa-19um03obhhhy4/base-recommendations/security-recommendation-set.json --> ./app_data/security-recommendation-set.json
[INFO] - Loading current portfolio
[INFO] - Downloading Portfolio: s3://app-infra-base-sadatabucketcc1b0cfa-19um03obhhhy4/portfolios/current-portfolio.json --> ./app_data/current-portfolio.json
[INFO] - Loaded recommendation set id: cfa3823a-8455-11ea-a0a5-acbc329ef75f
[INFO] - Repricing portfolio
[INFO] - Repriced portfolio for date of 2020-04-23 00:00:00
[INFO] - Portfolio is still current. No rebalancing necessary
[INFO] - updated portfolio: {
    "portfolio_id": "d645eaec-8455-11ea-b1d4-acbc329ef75f",
    "set_id": "cfa3823a-8455-11ea-a0a5-acbc329ef75f",
    "creation_date": "2020-04-22T04:57:59.021471+00:00",
    "price_date": "2020-04-23T04:00:00+00:00",
    "securities_set": [],
    "current_portfolio": {
        "securities": [
            {
                "ticker_symbol": "BA",
                "quantity": 0,
                "purchase_date": null,
                "purchase_price": 136.33,
                "current_price": 137.74,
                "current_returns": 0.010342551162620062
            },
            {
                "ticker_symbol": "GE",
                "quantity": 0,
                "purchase_date": null,
                "purchase_price": 6.48,
                "current_price": 6.52,
                "current_returns": 0.006172839506172645
            },
            {
                "ticker_symbol": "XOM",
                "quantity": 0,
                "purchase_date": null,
                "purchase_price": 40.96,
                "current_price": 43.45,
                "current_returns": 0.060791015625
            }
        ]
    }
}
[INFO] - Saving updated portfolio
[INFO] - Uploading Portfolio to S3: s3://app-infra-base-sadatabucketcc1b0cfa-19um03obhhhy4/portfolios/current-portfolio.json
[INFO] - Publishing portfilio update to SNS topic: arn:aws:sns:us-east-1:252849529410:sa-app-notifications-topic
```

After updating the portfolio a notification will be sent to SNS with the selected portfolio and its current returns. This results in the following email.

```
From: sa-app-notification-topic (no-reply@sns.amazonaws.com)
To: Me

Portfolio was created on: 2020/04/22 04:57 AM
Price date is: 2020/04/23

Symbol: BA
Simulated Purchase Price: 136.33
Current Price: 137.74 (+1%)

Symbol: GE
Simulated Purchase Price: 6.48
Current Price: 6.52 (+1%)

Symbol: XOM
Simulated Purchase Price: 40.96
Current Price: 43.45 (+6%)
```

# Running the Services
This section describes how to run the services either locally using Docker, or using ECS. The latter, specifically AWS Fargate, is the intended runtime platform for these services.

## Running the service as a docker image
It is possible to package the services as a Docker image. To build the container, run the ```docker_build.sh```. This command will build both Stock Advisor services, and you'll be able to run them locally.

```
>>./docker_build.sh
Sending build context to Docker daemon    126MB
Step 1/6 : FROM python:3.8-slim-buster
 ---> ee07b1466448
Step 2/6 : LABEL maintainer hanegraaff@gmail.com
 ---> Running in a684be7d3a89
Removing intermediate container a684be7d3a89
 ---> fa1bfe7dedbb
Step 3/6 : COPY ./src /app
 ---> 2b4972cee31b
Step 4/6 : WORKDIR /app
 ---> Running in cc780c1aca64
Removing intermediate container cc780c1aca64
 ---> 2c9d26ea0a28
Step 5/6 : RUN pip install -r requirements.txt
 ---> Running in 8e6d18a64ef7
...
Removing intermediate container 8e6d18a64ef7
 ---> b166ecddc400
Step 6/6 : ENTRYPOINT ["python", "recommendation_svc.py"]
 ---> Running in 3963296f1b3f
Removing intermediate container 3963296f1b3f
 ---> f1a79df20439
Successfully built f1a79df20439
Successfully tagged stock-advisor/recommendation_svc:v1.0.0
```
The resulting image will look like this:
```
>>docker images
REPOSITORY                         TAG                 IMAGE ID            CREATED             SIZE
stock-advisor/portfolio-manager    v1.0.0              def2c4dd97bd        32 seconds ago      435MB
stock-advisor/recommendation-svc   v1.0.0              4f443c16ccce        38 seconds ago      435MB
python                             3.8-slim-buster     56930ef6f6a2        2 weeks ago         193MB
```

Once built, the container is executed in a similar way as the script. Note how the ```INTRINIO_API_KEY``` must be supplied as a special environment variable. AWS credentials must also be supplied externally, in a similar way.

For example:

```
docker run -e INTRINIO_API_KEY=xxx image-id -ticker_file djia30.txt -output_size 3 production -app_namespace sa
```

## Running the service in ECS
This service is intended to be run in ECS using a Fargate task. The automation contained in the main project will create the ECS Cluster, Task Definitions, Scheduled Tasks, Container Repositories and CodeBuild project needed to build and deploy the service to AWS. Please refer to the main project for instructons on how to leverage automation to build and deploy the system.

Both the Recommendation Service and Portfolio manager are configured to run as scheduled tasks. The former is intended to run monthly and the latter daily, though this will likely change as development continues.

Tasks may be run on demand using the AWS console and navigating to the ECS Task defintions

![ECS Task Definitions](doc/ecs-tasks.png)

When running the task be sure to set the following:

1) Set the launch type to ```Fargate``` 
2) Select the VPC that was created using the automation. The CIDR block is 192.16.0.0/16, or you can check the tags to identify the proper one
3) Ensure the that a public IP address is auto assigned.

![ECS Task Definitions](doc/run-ecs-task-1.png)
![ECS Task Definitions](doc/run-ecs-task-2.png)

All application logs are stored inside CloudWatch.

# Unit Testing
You may run all unit tests using this command:

```./test.sh```

This command will execute all unit tests and run the coverage report (using coverage.py)

```
src >>./test.sh
......................................................................................................
----------------------------------------------------------------------
Ran 102 tests in 0.332s

OK
Name                                      Stmts   Miss  Cover
-------------------------------------------------------------
cloud/aws_service_wrapper.py                 70      7    90%
data_provider/intrinio_data.py              142     40    72%
data_provider/intrinio_util.py               27      0   100%
exception/exceptions.py                      32      1    97%
model/base_model.py                          59     10    83%
model/portfolio.py                           62      2    97%
model/recommendation_set.py                  45      0   100%
model/ticker_file.py                         44     10    77%
service_support/portfolio_mgr_svc.py         72      7    90%
service_support/recommendation_svc.py        29      3    90%
strategies/calculator.py                     19      0   100%
strategies/price_dispersion_strategy.py      68     29    57%
support/constants.py                         14      0   100%
support/financial_cache.py                   33      2    94%
support/util.py                              27      1    96%
-------------------------------------------------------------
TOTAL                                       743    112    85%
```