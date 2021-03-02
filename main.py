__author__ = "Tim Fagergren"

import requests
from time import sleep
import time
import csv
import sys
import ast

# This is the multiplier value that's used across the api, for currency prices and HNT amounts
MULTIPLIER = 100000000

# Delay to inject between API calls in loops, to prevent hitting rate limits
RATE_LIMIT_DELAY = 0.5

# Simple flag for enabling test-mode (precursor to unit tests)
TESTING = False

REWARDS_ACTIVITY_ORIGINAL_FILE="reward_activity_original.csv"
REWARDS_ACTIVITY_DOLLAR_PER_BLOCK="reward_activity_with_dollar_per_block.csv"


def does_file_exist(file):
    try:
        f = open(file)
        f.close()
        return True
    except Exception as error:
        print(error)
        return False


def get_price_at_block(block):
    """
    For a given block, returns something like this:
    {
      "data": {
        "price": 167000000,
        "block": 471570
      }
    }
    Ref: https://docs.helium.com/api/blockchain/oracle-prices
    :param block:
    :return: tuple of price and timestamp
    """
    price = requests.get(f"https://api.helium.io/v1/oracle/prices/{int(float(block))}")
    if price.status_code == requests.codes.all_good:
        print(f"Price at block: {block}: {price.json()['data']['price'] / MULTIPLIER} at {price.json()['data']['timestamp']}")
        return price.json()["data"]["price"], price.json()['data']['timestamp']
    else:
        print(f"Failed to get price for block {block}. HTTP Status code: {price.status_code}")


class PullTransactions:
    """

    """

    hnt_block_rewards = []
    other_activity = []
    reward_activity = []
    account_address = None
    pull_from_csv = False
    using_cache = {
        'transactions_for_account': False,
        'dollar_per_block': False
    }

    def __init__(self, account_address, pull_from_csv=False):
        self.hnt_block_rewards = []
        self.account_address = account_address
        self.pull_from_csv = pull_from_csv

    def get_transactions_for_account(self):
        """
        Filter out just the transactions (rewards) for given account
        :return:
        """
        print("----------------------------------------------------")
        print(f"Get transactions for account: {self.account_address}")
        activity = []
        if does_file_exist(REWARDS_ACTIVITY_ORIGINAL_FILE):
            print("Reading from cache..")
            self.using_cache['transactions_for_account'] = True
            with open(REWARDS_ACTIVITY_ORIGINAL_FILE, "r") as f:
                csv_reader = csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC)
                for row in csv_reader:
                    activity.append(row)
            self.reward_activity = activity
        else:
            print("Local cache does not exist - pulling from API..")
            api_endpoint = f"https://api.helium.io/v1/accounts/{self.account_address}/activity"
            response = requests.get(api_endpoint)
            while response.status_code == requests.codes.all_good and "cursor" in response.json().keys():
                activity.extend(response.json()['data'])
                response = requests.get(f"{api_endpoint}?cursor={response.json()['cursor']}")
                sleep(RATE_LIMIT_DELAY)
                print(len(activity))
                if len(activity) > 1 and TESTING is True:
                    # Short circuit when testing
                    break

            self.reward_activity = [item for item in activity if "reward" in item["type"]]
            # self.other_activity = [item for item in activity if "reward" not in item["type"]] # E.g. payment_v2

        print(self.reward_activity[0])
        print("----------------------------------------------------")

    def compile_rewards_per_block(self):
        """
        This creates a simplified list of total amount of HNT generated at the block level

        Allows for later assigning dollar values per block
        :return:
        """
        print("----------------------------------------------------")
        print(f"Compiling rewards per block..")
        for idx, block in enumerate(self.reward_activity):
            if self.using_cache['transactions_for_account'] is True:
                block['rewards'] = ast.literal_eval(block['rewards'])
            # SUM of all the rewards for a given block -> reward_total
            self.reward_activity[idx]['reward_total'] = sum((item['amount'] / MULTIPLIER) for item in block["rewards"])
        print(f"Compilation of rewards per block completed.")
        print("----------------------------------------------------")

    def set_dollar_per_block(self):
        """
        Assign a dollar value to each block
        :return:
        """
        print("----------------------------------------------------")
        print("Setting the dollar value per block")
        if does_file_exist(REWARDS_ACTIVITY_DOLLAR_PER_BLOCK):
            print("Reading from cache..")
            self.using_cache['dollar_per_block'] = True
            activity = []
            with open(REWARDS_ACTIVITY_DOLLAR_PER_BLOCK, "r") as f:
                csv_reader = csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC)
                for row in csv_reader:
                    activity.append(row)
            self.reward_activity = activity
        else:
            for idx, block in enumerate(self.reward_activity):
                self.reward_activity[idx]['price'], self.reward_activity[idx]['price_time'] = \
                    get_price_at_block(block['height'])
                # Format usd_total into user-friendly value, retaining decimal points
                self.reward_activity[idx]['usd_total'] = self.reward_activity[idx]['reward_total'] \
                                                         / MULTIPLIER * self.reward_activity[idx]['price']
                sleep(RATE_LIMIT_DELAY)
        print("----------------------------------------------------")

    def store_to_csv(self, file_type="reward_activity", suffix=""):
        data = self.__getattribute__(file_type)
        with open(f"{file_type}_{suffix}.csv", 'w', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(data[0].keys())
            for line in data:
                values = [f"{item:.20f}" if (isinstance(item, int) is True or isinstance(item, float) is True)
                          else item for item in line.values()]
                writer.writerow(values)
            f.close()

    def output_to_csv_all_rewards(self):
        """
        Returns the itemized list of rewards in a csv format - in the current working directory
        :return:
        """
        headers = ["height", "price", "price_time", "reward_total", "usd_total"]
        with open(f"rewards_only.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for line in self.reward_activity:
                # Separate out only the keys we actually have
                line["price"] = int(float(line["price"])) / MULTIPLIER
                values = [line[key] if key in line.keys() else "" for key in headers]
                # Ensure non scientific formatting
                values = [f"{item:.20f}" if (isinstance(item, int) is True or isinstance(item, float) is True)
                          else item for item in values]
                writer.writerow(values)
            f.close()

    def output_total_rewards_for_year(self, year):
        """

        :param year:
        :return:
        """
        start_time = time.strptime(f"{year}-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
        end_time = time.strptime(f"{year}-12-31 23:59:59", "%Y-%m-%d %H:%M:%S")
        start_time_epoch = time.mktime(start_time)
        end_time_epoch = time.mktime(end_time)

        total_rewards = 0.00
        for reward_block in self.reward_activity:
            if "usd_total" not in reward_block.keys() \
                    or str(reward_block["usd_total"]).strip() == "" \
                    or reward_block["usd_total"] is None:
                print(f"Something went wrong! This block ({reward_block['height']}) is lacking a usd_total value - this is a required key.")
                sys.exit(1)
            if start_time_epoch <= int(float(reward_block['time'])) <= end_time_epoch:
                total_rewards += float(reward_block['usd_total'])
                print(f"Adding block from: {reward_block['price_time']}: {total_rewards}")

        return total_rewards


account_id = sys.argv[1]
year = sys.argv[2]
main = PullTransactions(account_id)
main.get_transactions_for_account()
main.store_to_csv("reward_activity", "original")
main.compile_rewards_per_block()
main.set_dollar_per_block()
main.store_to_csv("reward_activity", "with_dollar_per_block")
main.output_to_csv_all_rewards()
print(main.output_total_rewards_for_year(year))