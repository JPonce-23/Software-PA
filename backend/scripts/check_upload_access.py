"""Read-only deployment preflight. Run as the runtime UID against its mount.

Never changes ownership/modes, opens file contents, repairs or recreates locks.
Output contains counts/codes only. Actual requests retain descriptor checks.
"""
import argparse
import os
from pathlib import Path
import stat


def check(root):
    if os.geteuid() != 10001:
        raise ValueError("RUNTIME_UID_REQUIRED")
    root = Path(root)
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError("CANONICAL_ROOT_REQUIRED")
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 10001
            or info.st_mode & 0o022 or not os.access(root, os.R_OK | os.W_OK | os.X_OK)):
        raise ValueError("ROOT_ACCESS_REQUIRED")
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        path = Path(directory)
        coordination = path == root / '.ss12-writers'
        for name in dirs + files:
            count += 1
            if count > 1000000:
                raise ValueError("PREFLIGHT_ENTRY_BUDGET")
            item = path / name
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError("SYMLINK_REQUIRES_REVIEW")
            if stat.S_ISDIR(info.st_mode):
                if not os.access(item, os.R_OK | os.W_OK | os.X_OK) or info.st_mode & 0o022:
                    raise ValueError("DIRECTORY_ACCESS_REQUIRED")
                if item == root / '.ss12-writers' and (info.st_uid != 10001 or stat.S_IMODE(info.st_mode) != 0o700):
                    raise ValueError("COORDINATION_DIRECTORY_REQUIRED")
            elif stat.S_ISREG(info.st_mode):
                if not os.access(item, os.R_OK) or info.st_mode & 0o022:
                    raise ValueError("FILE_ACCESS_REQUIRED")
                if coordination and (info.st_uid != 10001 or stat.S_IMODE(info.st_mode) != 0o600
                        or info.st_size or info.st_nlink != 1):
                    raise ValueError("COORDINATION_FILE_REQUIRED")
            else:
                raise ValueError("SPECIAL_FILE_REQUIRES_REVIEW")
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=os.getenv('UPLOAD_ROOT', '/app/uploads'))
    args = parser.parse_args()
    try:
        count = check(args.root)
    except (ValueError, OSError) as error:
        print('UPLOAD_PREFLIGHT_FAIL', str(error) if isinstance(error, ValueError) else 'FILESYSTEM_ACCESS')
        raise SystemExit(1)
    print('UPLOAD_PREFLIGHT_OK', count)
