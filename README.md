# Twitter Conversation Crawler

An easy implementation of crawling conversational tweet threads.
You may use it for building dialog datasets for training chatbots based on machine learning.

This requires BEARER_TOKEN of Twitter Developer API v2.


## Crawl

Modify `LANG = "en"` in `search.py`, if you want tweets in other languages like Japanese ("ja").

```
export BEARER_TOKEN='_____YOUR_BEARER_TOKEN_HERE_____'
python -u search.py > tweets.jsonl
```


## Extract Conversation Chains

```
python process.py < tweets.jsonl > convs.jsonl
```


### Velocity

- The twitter API has a MONTHLY TWEET CAP USAGE (typically, 500000/month).
  - You can check the remaining MONTHLY TWEET CAP USAGE on the [Dashboard](https://developer.twitter.com/en/portal/dashboard).
  - (And also, it has the caps of the number of requests per 15-minute. See [the doc](https://developer.twitter.com/en/docs/twitter-api/rate-limits).)
- One loop usually accesses around 100 tweets with variances.
- So, we can run 7 loops per hour at maximum (500000/30/24/100 = 6.94...).
- The default velocity is set as 5 loops per hour (12 min interval). If you wanna change, modify `search.py`.



## Data examples

#### a line of `tweets.jsonl`

```
{
  "data": [
    {
      "author_id": "2879237869",
      "conversation_id": "1362605931436019724",
      "created_at": "2021-02-19T11:57:29.000Z",
      "entities": {
        "mentions": [
          {
            "end": 9,
            "start": 0,
            "username": "xcanamem"
          },
          {
            "end": 23,
            "start": 10,
            "username": "xbeniha_trpg"
          }
        ]
      },
      "id": "1362733036882649088",
      "in_reply_to_user_id": "1273448559900110848",
      "lang": "ja",
      "possibly_sensitive": false,
      "referenced_tweets": [
        {
          "id": "1362731511473086465",
          "type": "replied_to"
        }
      ],
      "reply_settings": "following",
      "source": "Twitter for Android",
      "text": "@xcanamem @xbeniha_trpg わーい。ありがとうございます！
    },
    {
      "author_id": "1273448559900110848",
      "conversation_id": "1362605931436019724",
      "created_at": "2021-02-19T11:51:25.000Z",
      ...
      "text": "@xbeniha_trpg3 @xKanraKor 愛しています！"
    },
    ...
  ],
  "includes": {
    "users": [
      {
        "created_at": "2014-10-27T07:40:58.000Z",
        "description": "TRPG専用垢。",
        "id": "2879237869",
        "name": "あいうえお太郎",
        "protected": false,
        "public_metrics": {
          "followers_count": 44,
          "following_count": 52,
          "listed_count": 1,
          "tweet_count": 5287
        },
        "username": "xKanraKoro"
      },
      ...
    ]
  },
  "meta": {
    "newest_id": "1362733036882649088",
    "next_token": "b26v89c19zqg8o3fosns33kwp7sfdsafsacdscscdsafsa",
    "oldest_id": "1362728096110022663",
    "result_count": 10
  }
}
```

#### a line of `convs.jsonl`

```
[
  {
    "author_id": "2879237869",
    "conversation_id": "1362605931436019724",
    "created_at": "2021-02-19T11:37:51.000Z",
    ...
    "text": "@xcanamemm @xbeniha_trpg3 任せました！"
  },
  {
    "author_id": "1340661951769104384",
    "conversation_id": "1362605931436019724",
    "created_at": "2021-02-19T11:38:45.000Z",
    ...
    "text": "@xKanraKoro @xcanamemm 了解です！！！"
  },
  ...
]
```
