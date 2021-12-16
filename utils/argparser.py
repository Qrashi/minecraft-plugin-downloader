import argparse

parser = argparse.ArgumentParser(description='Update all dependencies')
parser.add_argument('--check-all-compatibility', dest='check_all_compatibility', action="store_true", default=False,
                    help='Check all compatibilities for all dependencies')
args = parser.parse_args()
