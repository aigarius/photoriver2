#!/usr/bin/env python3
import logging

from photoriver2.config import parse_config, init_remotes

logger = logging.getLogger("main")


# pylint: disable=too-many-branches
def main():
    """Run the normal process"""
    config_data = parse_config()
    remotes = init_remotes(config_data)
    for remote in remotes:
        fixes = remotes[remote].get_fixes()
        if config_data["options"]["dry_run"]:
            print(fixes)
        else:
            remotes[remote].do_fixes(fixes)
        remotes[remote].get_new_state()
    updates = []
    for remote in remotes:
        updates.extend(remotes[remote].get_updates())
    if config_data["options"]["dry_run"]:
        print(updates)
    else:
        for remote in remotes:
            remotes[remote].do_updates(updates)
    for remote1 in remotes:
        for remote2 in remotes:
            if remote1 == remote2:
                continue
            merges = remotes[remote1].get_merge_updates(remotes[remote2])
            if config_data["options"]["dry_run"]:
                print(merges)
            else:
                remotes[remote1].do_updates(merges)
    if not config_data["options"]["dry_run"]:
        for remote in remotes:
            remotes[remote].save_new_state()


if __name__ == "__main__":
    logging.basicConfig()
    main()
