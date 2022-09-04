#!/usr/bin/env python3
import argparse
import logging
import os

from photoriver2.config import parse_config, init_remotes

logger = logging.getLogger("photoriver2")


def parse_args():
    parser = argparse.ArgumentParser(description="Photoriver2 photo sync program")

    parser.add_argument("--dry-run", action="store_true", help="Do not do any photo changs, print actions to be taken")
    parser.add_argument("--init-only", action="store_true", help="Stop after connecting to all remotes")
    parser.add_argument("--sync-only", action="store_true", help="Stop after fetching new state from all remotes")
    parser.add_argument("--skip-sync", action="store_true", help="Skip fetching new state from all remotes")
    parser.add_argument("--fixes-only", action="store_true", help="Stop after applying normalising fixes")
    parser.add_argument("--no-state-cache", action="store_true", help="Ignore cached state from all remotes")
    parser.add_argument("--pull-only", action="store_true", help="Only pull missing photos from other remotes to base")
    parser.add_argument("--push-only", action="store_true", help="Only push missing photos to other remotes from base")

    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO)
    options = parse_args()
    logger.info("Parsing config")
    if os.path.exists("/river/config"):
        config_path = "/river/config"
    elif os.path.exists(os.path.expanduser("~/.config/photoriver2")):
        config_path = os.path.expanduser("~/.config/photoriver2")
    config_data = parse_config(config_path)
    logger.info("Starting all remotes")
    remotes = init_remotes(config_data)
    if options.init_only:
        logger.info("Init complete - exiting")
        return
    logger.info("Getting new state of all remotes")
    if not options.skip_sync:
        for remote in remotes:
            logger.info("Getting new state for remote %s", remote)
            remotes[remote].get_new_state(no_state_cache=options.no_state_cache)
    if options.sync_only:
        logger.info("State sync complete - exiting")
        return
    for remote in remotes:
        logger.info("Fixes for remote %s", remote)
        fixes = remotes[remote].get_fixes()
        if options.dry_run:
            print(fixes)
        else:
            remotes[remote].do_fixes(fixes)
    if options.fixes_only:
        logger.info("Fixes complete - exiting")
        return
    if not options.push_only:
        logger.info("Starting pulling new photos to base from remotes")
        for remote in remotes:
            if remote == "base":
                continue
            logger.info("Finding pull merges for %s", remote)
            merges = remotes["base"].get_merge_updates(remotes[remote])
            if options.dry_run:
                print(merges)
            else:
                logger.info("Applying pull merges from %s to base", remote)
                remotes["base"].do_updates(merges)
        logger.info("Applying all pull merges - done")
    if not options.pull_only:
        logger.info("Starting pushing new photos from base to remotes")
        for remote in remotes:
            if remote == "base":
                continue
            logger.info("Finding push merges for %s", remote)
            merges = remotes[remote].get_merge_updates(remotes["base"])
            if options.dry_run:
                print(merges)
            else:
                logger.info("Applying pull merges to %s from base", remote)
                remotes[remote].do_updates(merges)
        logger.info("Applying all pull merges - done")
    logger.info("Sync completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
