import json
import sys
from collections import defaultdict
from logging import DEBUG, INFO, WARNING, basicConfig, getLogger

fmt = "[%(asctime)s][%(levelname)s] %(message)s"
basicConfig(level=DEBUG, format=fmt)
logger = getLogger(__name__)


def main(print_text_only=False):
    for l in sys.stdin:
        conv_replies_data = json.loads(l.strip())
        logger.info(
            f"process: {conv_replies_data['data'][0]['conversation_id']}, {len(conv_replies_data['data'])} tweets"
        )
        tweet_dict = {}
        ref_from_dict = defaultdict(list)
        ref_to_dict = defaultdict(list)
        tweet_list = conv_replies_data["data"]
        for tweet in tweet_list:
            logger.debug(
                " ({} -> {}) tweet: {}".format(
                    tweet["author_id"],
                    tweet.get("in_reply_to_user_id", "NONE"),
                    tweet["text"].replace("\n", "\t"),
                )
            )
            if (
                "in_reply_to_user_id" in tweet
                and tweet["in_reply_to_user_id"] == tweet["author_id"]
            ):
                # skip self-reply
                logger.debug(f" skip self-reply")
                continue
            # TODO: if you want, add more filtering based on user fileds or other tweet fields
            tweet_dict[tweet["id"]] = tweet
            if "referenced_tweets" in tweet:
                for ref in tweet["referenced_tweets"]:
                    if ref["type"] == "replied_to":
                        ref_from_dict[ref["id"]].append(tweet["id"])
                        ref_to_dict[tweet["id"]].append(ref["id"])

        root_tweet_ids = set(tweet_dict.keys()) - set(ref_to_dict)
        if not root_tweet_ids:
            # if no root tweet is found, the root tweet has different conversation id and missing.
            # so, this searches for tweets, which failed to find ref
            logger.debug(
                f" root tweet is not found. so searching for tweets with no reply target."
            )
            for source_id, target_ids in ref_to_dict.items():
                if not any(idx in tweet_dict for idx in target_ids):
                    root_tweet_ids.add(source_id)

        def traverse_chains(current_chain, next_id):
            next_chain = current_chain + [tweet_dict[next_id]]
            reply_ids = ref_from_dict[next_id]
            if not reply_ids:
                yield next_chain
            else:
                for referring_id in reply_ids:
                    for complete_chain in traverse_chains(next_chain, referring_id):
                        yield complete_chain

        chains = []
        for root_tweet_id in root_tweet_ids:
            for chain in traverse_chains([], root_tweet_id):
                if len(chain) >= 2:
                    chains.append(chain)

        for chain in chains:
            logger.debug(f" -------chain-start")
            if print_text_only:
                print(
                    "\t".join(
                        tw["text"].replace("\n", " ").replace("\t", " ") for tw in chain
                    )
                )
            else:
                print(json.dumps(chain, sort_keys=True))
            for tw in chain:
                logger.debug("  {}".format(tw["text"].replace("\n", " ")))
            logger.debug(f" =======end========")
        logger.info(
            " print chains of lengths {}".format([len(chain) for chain in chains])
        )
        logger.info(
            " unique tweets {}".format(len(set([tw["id"] for tw in sum(chains, [])])))
        )


if __name__ == "__main__":
    # print lines of conversational json (a list of tweets) if print_text_only=False
    # print "\t"-concatenations of conversational texts if print_text_only=True
    main(print_text_only=False)
