# helium-transaction-overview
I created this for use in compiling details needed to file taxes. Use for recreation only :)  I accept no liability or offer any guarantees for the contents of this repository.

## Prerequisites

- Python 3
- Your account ID
  - Find by navigating to: https://explorer.helium.com/
  - In the search bar, type in your hotspot name (any of them if you have multiple)
  - Search the result page for "Owned By: ", and click on that
  - Now you have your Account ID
- Time: This takes a while to pull your reward history. Took me ~3 hours 

## Usage

1) Git Clone / Checkout locally
2) `pip install -r requirements.txt`
  - Recommend to use something like virtual env (venv)
3) `python main.py <account_id> <year>`

Example:

```sh
git clone https://github.com/timfagergren/helium-transaction-overview.git
cd helium-transaction-overview
pip install -r requirements.txt
## Replace with your account_id, don't use this one
python main.py 13jFKYu3ywLHzJxdTMDENqnutTo5cEdLs8cQGYeatQSkhWYbDUc 2020
```

## Considerations

### Rate limiting
This will pull details from Heliums official APIs, which are subject to rate limits.  If you start to get rate limited, 
I would suggest increasing the RATE_LIMIT_DELAY value in `main.py`.

### Caching
Results are stored in .csv files within the same directory. To re-pull fresh in case the script failed early, delete the
.csv files and start fresh.

* The first file created is `reward_activity_original.csv`, which is the direct results from the Helium API relating to your hotspot(s).
* The second file created is `reward_activity_with_dollar_per_block.csv`, which is a copy of `reward_activity_original.csv`
 but appended to it the dollar values
 
The second process of assigning the dollar values per block definitely takes much longer.
  
If an error occurs during the second file creation, but not the first - it's better to delete the second file only and 
use the cache from the first file instead of hitting the API again.
