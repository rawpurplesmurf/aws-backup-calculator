#!/usr/bin/env python3
import argparse
import sys

import boto3
from botocore.exceptions import ClientError

def get_snapshot_percentage(ec2, snapshot_id):
    # 1) Describe the snapshot to get the source volume size (GiB)
    try:
        resp = ec2.describe_snapshots(SnapshotIds=[snapshot_id])
    except ClientError as e:
        print(f"ERROR describing {snapshot_id}: {e}", file=sys.stderr)
        return None

    snaps = resp.get('Snapshots', [])
    if not snaps:
        print(f"Snapshot {snapshot_id} not found.", file=sys.stderr)
        return None

    volume_size_gib = snaps[0]['VolumeSize']

    # 2) Paginate ListSnapshotBlocks to count how many 512 KiB blocks are stored
    paginator = ec2.get_paginator('list_snapshot_blocks')
    block_count = 0
    try:
        for page in paginator.paginate(SnapshotId=snapshot_id):
            blocks = page.get('Blocks', [])
            block_count += len(blocks)
    except ClientError as e:
        print(f"ERROR listing blocks for {snapshot_id}: {e}", file=sys.stderr)
        return None

    # 3) Compute sizes
    BYTES_PER_BLOCK = 512 * 1024
    snapshot_bytes = block_count * BYTES_PER_BLOCK
    volume_bytes   = volume_size_gib * 1024**3

    percent = (snapshot_bytes / volume_bytes) * 100 if volume_bytes else 0.0
    return {
        'snapshot_id': snapshot_id,
        'volume_size_gib': volume_size_gib,
        'blocks_stored': block_count,
        'snapshot_bytes': snapshot_bytes,
        'volume_bytes': volume_bytes,
        'percent': percent
    }

def main():
    parser = argparse.ArgumentParser(
        description="For each EBS snapshot ID, compute what % of its source volume was actually stored.")
    parser.add_argument(
        '--region', '-r', default=None,
        help="AWS region (will use default if unset)")
    parser.add_argument(
        'snapshots', metavar='SNAPSHOT_ID', nargs='+',
        help="One or more EBS snapshot IDs")
    args = parser.parse_args()

    ec2 = boto3.client('ec2', region_name=args.region)

    for snap_id in args.snapshots:
        result = get_snapshot_percentage(ec2, snap_id)
        if not result:
            continue
        print(f"{result['snapshot_id']}: "
              f"{result['percent']:.2f}% "
              f"({result['blocks_stored']} blocks, "
              f"{result['snapshot_bytes']:,} bytes of {result['volume_bytes']:,} bytes)")
    
if __name__ == '__main__':
    main()

