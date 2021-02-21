# coding: utf-8
import datetime
import json
import os
import time
from logging import DEBUG, INFO, WARNING, basicConfig, getLogger

import requests

fmt = "[%(asctime)s][%(levelname)s] %(message)s"
basicConfig(level=DEBUG, format=fmt)
logger = getLogger(__name__)

getLogger("urllib3").setLevel(WARNING)

# LANG = "ja"
LANG = "en"


def auth():
    return os.environ.get("BEARER_TOKEN")


# Twitter search API requires some query (i.e., empty is not allowed)
# So, this uses the negation query with a garbage string, which would be matched with nothing
GARBAGE_STRING = '"jdsoavndksaofjdsfadsakfjo"'


def create_url_of_searching_for_replies(start_time, end_time):
    # Query
    # note: this negation may not always work well and leakage could happen. (longer query is stable?)
    # if you wanna filter out completely, check by yourself after fetch.
    if LANG == "ja":
        negations = [
            "おは",
            "おはよ",
            "おはよう",
            "あり",
            "がんば",
            "頑張り",
            "頑張れ",
            "頑張って",
            "おめでとう",
            "ありがとう",
            "誕生日",
            "いってら",
            "おやすみ",
            "お休み",
            "おつ",
            "おつかれ",
            "お疲れ",
            "ござい",
            "こんに",
            "こんば",
            "よろしく",
        ]
        negations_query = " ".join(f'-"{q}"' for q in negations)
    else:
        negations_query = ""
    query = f"-{GARBAGE_STRING} {negations_query} is:reply lang:{LANG} -is:quote -has:hashtags -has:media -has:links"

    # Fields are adjustable.
    tweet_fields = "tweet.fields=author_id,conversation_id,in_reply_to_user_id,possibly_sensitive,created_at,entities,lang,referenced_tweets,reply_settings,source,context_annotations,withheld"
    user_fields = "user.fields=created_at,public_metrics,description,username,name,id,protected,withheld"
    expansions = "expansions=author_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id"

    # Maximum number of results in a page
    max_results = 20

    # Concat them as URL
    url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&{expansions}&{tweet_fields}&{user_fields}&max_results={max_results}&start_time={start_time}&end_time={end_time}"
    return url


def create_url_of_conversation(conversation_id):
    query = f"conversation_id:{conversation_id}"
    tweet_fields = "tweet.fields=author_id,conversation_id,in_reply_to_user_id,possibly_sensitive,created_at,entities,lang,referenced_tweets,reply_settings,source,context_annotations,withheld"
    user_fields = "user.fields=created_at,public_metrics,description,username,name,id,protected,withheld"
    expansions = "expansions=author_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id"
    # with expansions=referenced_tweets.id, we can fetch the root tweet of the conversation too (it is in data["includes"]["tweets"])
    max_results = 10
    url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&{expansions}&{tweet_fields}&{user_fields}&max_results={max_results}"
    return url


def create_url_of_root_of_conversation(conversation_id):
    query = f"id:{conversation_id}"
    tweet_fields = "tweet.fields=author_id,conversation_id,in_reply_to_user_id,possibly_sensitive,created_at,entities,lang,referenced_tweets,reply_settings,source,context_annotations"
    user_fields = "user.fields=created_at,public_metrics,description,username,name,id,protected,withheld"
    expansions = "expansions=author_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id"
    max_results = 10
    url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&{expansions}&{tweet_fields}&{user_fields}&max_results={max_results}"
    return url


def create_headers():
    bearer_token = auth()
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def as_id_dict(list_data):
    return {d["id"]: d for d in list_data}


def get_stripped_text_without_noisy_entities(data):
    # strip mentions and urls
    # note: this just strips rather than replacing it with placeholders
    # e.g. "@someuser hello" -> "hello", "BTW, @someuser said hello" -> "BTW, said hello"
    text = data["text"]
    if "entities" not in data:
        return text
    noisy_entities = data["entities"].get("mentions", []) + data["entities"].get(
        "urls", []
    )
    for m in sorted(noisy_entities, key=lambda x: -x["start"]):  # iterate from the tail
        text = text[: m["start"]] + text[m["end"] + 1 :]
    return text


def is_bad_conversation_element(data, includes):
    if "entities" in data and "urls" in data["entities"]:
        # url tweet is often noisy
        logger.debug(f" url tweet")
        return True
    if data["possibly_sensitive"]:
        logger.debug(f" possibly sensitive")
        return True
    if (
        "entities" in data
        and "mentions" in data["entities"]
        and len(data["entities"]["mentions"]) >= 4
    ):
        # skip many-multi-party conversation due to complexity
        logger.debug(f' len(data["entities"]["mentions"]) >= 4')
        return True
    if data["author_id"] == data["in_reply_to_user_id"]:
        # skip self-reply
        logger.debug(f' data["author_id"] == data["in_reply_to_user_id"]')
        return True
    if len(set(get_stripped_text_without_noisy_entities(data))) <= 10:
        logger.debug(f" too short text")
        return True
    users_dict = as_id_dict(includes["users"])
    if data["in_reply_to_user_id"] not in users_dict:
        logger.debug(f' data["in_reply_to_user_id"] not in users_dict')
        return True
    if users_dict[data["in_reply_to_user_id"]]["protected"]:
        # skip conversation with private accounts
        logger.debug(f" private accounts")
        return True
    if (
        users_dict[data["in_reply_to_user_id"]]["public_metrics"]["followers_count"]
        >= 5000
    ):
        # skip reply to celebrity
        logger.debug(f" high followers count")
        return True
    if (
        users_dict[data["in_reply_to_user_id"]]["public_metrics"]["following_count"]
        <= 5
        or users_dict[data["in_reply_to_user_id"]]["public_metrics"]["followers_count"]
        <= 5
    ):
        # skip reply to low-following or low-follower accounts
        logger.debug(f" low follower or following counts")
        return True
    return False


def is_bad_conversation(data):
    if "data" not in data or len(data["data"]) <= 1:
        # fetch error
        logger.debug(f' "data" not in data or len(data["data"]) <= 1')
        return True
    if len(data["includes"]["users"]) >= 7:
        # skip many-multi-party conversation due to complexity
        # skip conversation, where many persons replies to a single person (e.g. celebrity)
        logger.debug(f' len(data["includes"]["users"]) >= 7')
        return True
    if (
        len(data["includes"]["users"]) == 1
        or len(set([tw["in_reply_to_user_id"] for tw in data["data"]])) == 1
    ):
        # skip self-reply
        # skip conversation with private accounts
        logger.debug(
            f' len(data["includes"]["users"]) == 1 or len(set([tw["in_reply_to_user_id"] for tw in data["data"]])) == 1'
        )
        return True
    return False


def fetch_conversations(tweets_data):
    tweet_list = tweets_data["data"]
    # meta = tweets_data["meta"]
    includes = tweets_data["includes"]
    headers = create_headers()
    for d in tweet_list:
        conv_id = d["conversation_id"]
        logger.info(f"process {conv_id}")
        logger.debug(f" text: {d['text']}")
        if is_bad_conversation_element(d, includes):
            logger.info(f" skip conversation {conv_id} as pruning")
            continue
        url = create_url_of_conversation(conv_id)
        logger.debug(f"connect to URL: {url}")
        conv_replies_data = connect_to_endpoint(url, headers)
        if is_bad_conversation(conv_replies_data):
            logger.info(f" skip conversation {conv_id} as filtering")
            continue
        if (
            "includes" in conv_replies_data
            and "tweets" in conv_replies_data["includes"]
        ):
            # root tweet of the conversation is in conv_replies_data["includes"]["tweets"]
            # move it into conv_replies_data["data"] list
            for tw in conv_replies_data["includes"]["tweets"]:
                if tw["id"] == conv_id:
                    conv_replies_data["data"].append(tw)
                    break
            del conv_replies_data["includes"]["tweets"]  # for efficiency
        logger.info(f" print conversation {conv_id}")
        print(json.dumps(conv_replies_data, sort_keys=True))


def main():
    loop_count = 0
    loop_limit = 100000
    error_count = 0
    error_limit = 100
    sec_per_day = 24 * 60 * 60
    time_seconds_limit = 365 * sec_per_day
    time_days_limit = time_seconds_limit / sec_per_day

    # config
    search_old_offset = datetime.timedelta(days=2)
    period_minutes = 12
    search_duration = datetime.timedelta(minutes=period_minutes)
    sleep_seconds = period_minutes * 60
    sleep_seconds_when_error = 10 * 60
    logger.info(
        f"offset: {search_old_offset}, period_minutes: {period_minutes}, loop limit: {loop_limit}, error limit: {error_limit}, time limit: {time_days_limit} days"
    )

    # init start time
    search_start_time = datetime.datetime.now() - search_old_offset
    headers = create_headers()
    launch_time = time.time()
    while (
        loop_count < loop_limit
        and error_count < error_limit
        and (time.time() - launch_time) < time_seconds_limit
    ):
        search_end_time = search_start_time + search_duration
        search_start_time_str = search_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        search_end_time_str = search_end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = create_url_of_searching_for_replies(
            start_time=search_start_time_str, end_time=search_end_time_str,
        )
        logger.info(f"search: {search_start_time_str} TO {search_end_time_str}")
        logger.info(f"connect to URL: {url}")
        try:
            replies_data = connect_to_endpoint(url, headers)  # dict
            fetch_conversations(replies_data)
        except Exception as e:
            logger.warning(f"failed {e}")
            logger.info(f"sleep: {sleep_seconds_when_error} sec")
            error_count += 1
            time.sleep(sleep_seconds_when_error)
        search_start_time = search_start_time + search_duration
        loop_count += 1
        logger.info(
            f"limit: (loop {loop_count}/{loop_limit}) (error {error_count}/{error_limit}) (time days {int((time.time() - launch_time)/sec_per_day)}/{time_days_limit})"
        )
        logger.info(f"sleep: {sleep_seconds} sec")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
