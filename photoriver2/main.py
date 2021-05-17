#!/usr/bin/env python3
import logging

from photoriver2.config import parse_config, init_remotes

logger = logging.getLogger("main")


# pylint: disable=too-many-branches
def main():
    """Run the normal process"""
    logger.info("Parsing config")
    config_data = parse_config()
    logger.info("Starting all remotes")
    remotes = init_remotes(config_data)
    logger.info("Getting new state of all remotes")
    for remote in remotes:
        logger.info("Getting fixes for remote %s", remote)
        fixes = remotes[remote].get_fixes()
        if config_data["options"]["dry_run"]:
            print(fixes)
        else:
            remotes[remote].do_fixes(fixes)
        logger.info("Getting new state for remote %s", remote)
        remotes[remote].get_new_state()
    logger.info("Finding updates for all remotes")
    updates = []
    for remote in remotes:
        updates.extend(remotes[remote].get_updates())
    logger.info("Finding updates - done")
    if config_data["options"]["dry_run"]:
        print(updates)
    else:
        for remote in remotes:
            logger.info("Applying updates to remote %s", remote)
            remotes[remote].do_updates(updates)
    logger.info("Calculating all merges")
    for remote1 in remotes:
        for remote2 in remotes:
            if remote1 == remote2:
                continue
            logger.info("Finding merges for %s to %s", remote1, remote2)
            merges = remotes[remote1].get_merge_updates(remotes[remote2])
            if config_data["options"]["dry_run"]:
                print(merges)
            else:
                logger.info("Applying merges to %s", remote1)
                remotes[remote1].do_updates(merges)
    logger.info("Applying all merges - done")
    logger.info("Saving new state")
    if not config_data["options"]["dry_run"]:
        for remote in remotes:
            remotes[remote].save_new_state()
    logger.info("Saving new state - done")
    logger.info("All sync done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
