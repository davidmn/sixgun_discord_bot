import asyncio
import feedparser
import discord
import sys
import logging
from discord import Game
from tinydb import TinyDB, Query
try:
    from config import CONFIG
except ModuleNotFoundError:
    print("Could not find config.py")
    sys.exit(1)

client = discord.Client()

db = TinyDB(CONFIG["db_path"])


def episode_is_new(feed_url, episode_url):
    """
        Checks if a given podcast episode is a new episode.
        Episodes are identified via their URL.
        We check in the database if the url to check is the same as the one we have most recently
        seen for this feed, if not, we assume it is a new episode.
        If we have never seen any episode for this feed we assuem it's not new either.
    """
    Entry = Query()
    result = db.search(Entry.feed_url == feed_url)

    if len(result) == 0:
        db.insert({"feed_url": feed_url, "episode_url": episode_url})
        logging.info("This is the first episode for this feed. Assuming it's not new.")
        return False
    else:
        known_episode = result[0]
        if known_episode["episode_url"] == episode_url:
            return False
        else:
            db.update({"episode_url": episode_url}, Entry.feed_url == feed_url)
            return True


def get_latest_episode(url):
    """
        Parses the RSS feed for a given podcast url and returns the latest episode
    """
    feed = feedparser.parse(url)
    return feed.entries[0]


async def watch_feed(feedwatcher):
    """
        Watches a podcast feed and sends a message to that shows channel whenever a new
        entry appears.
    """
    await client.wait_until_ready()
    channel = discord.Object(id=feedwatcher.channel_id)
    while not client.is_closed:
        latest_episode = get_latest_episode(feedwatcher.feed_url)

        # find the URL to the episode
        for link in latest_episode.links:
            if link["rel"] == "alternate":
                episode_url = link["href"]
                break

        if episode_is_new(feedwatcher.feed_url, episode_url):

            message = "+++ I RECEIVED A NEW {1} DATAFRAME +++ \n {0}".format(
                episode_url, feedwatcher.show_name
            )
            await client.send_message(channel, message)
            logging.info(
                "Sent message for new episode for {0}".format(feedwatcher.show_name)
            )
        else:
            logging.info("No new episode for {0}".format(feedwatcher.show_name))
        await asyncio.sleep(CONFIG["feed_watch_interval"])


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    for watcher in CONFIG["feed_watchers"]:
        client.loop.create_task(watch_feed(watcher))
    client.run(CONFIG["TOKEN"])