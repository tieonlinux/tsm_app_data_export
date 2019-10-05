import argparse
import os
import platform
import re
import sys
from pathlib import Path

import pandas as pd
from lupa import LuaRuntime


class RetryLater(Exception):
    pass


def iter_dataframes(path):
    path = Path(path)
    lua = LuaRuntime(unpack_returned_tuples=False)

    assert path.exists()

    init_lua_file = Path(Path(__file__).parent, 'functions.lua')
    lua.execute(init_lua_file.read_text())
    with path.open('r') as f:
        line = True
        while line:
            line = f.readline()
            if len(line) < 5 and not line.strip():
                continue
            lua.execute('pre_hook()')
            try:
                lua.execute(line)
            except Exception as e:
                if 'LuaSyntaxError' in type(e).__name__:
                    # sometimes tsm write into the file at the same time we read it
                    raise RetryLater() from e
                else:
                    raise
            finally:
                lua.execute('post_hook()')

            data = lua.eval('_G.datastack')
            lua.execute('_G.datastack = nil')
            if not data:
                continue
            download_time = int(data.downloadTime)
            tag = data.tag
            realm = data.realm
            filename = f"tsm_{realm.lower().replace('-', '_').replace(' ', '_')}"
            print("processing %s" % realm)
            fields = tuple(data.fields.values())
            assert fields
            data = (sub.values() for sub in data.data.values())
            df = pd.DataFrame(data, columns=fields)

            if len(df) == 0:
                print("no data for %s" % filename)
                continue
            df['date'] = pd.to_datetime(download_time, unit='s')
            for col in ('marketValue', 'minBuyout', 'historical', 'numAuctions'):
                if col in df:
                    df[col] = pd.to_numeric(df[col], downcast='integer')

            df['itemString'] = df['itemString'].astype(str)
            yield filename, df


def export_dataframe(filename, df: pd.DataFrame, format='csv'):
    if filename == 'stderr':
        fn = sys.stderr
    elif isinstance(filename, (str, Path)):
        fn = str(filename)
        if not fn.endswith(f'.{format}'):
            fn = f'{fn}.{format}'
    else:
        fn = filename

    if format == 'csv':
        df.to_csv(fn, index=False)
    elif format in ('json', 'yml', 'yaml'):
        df.to_json(fn, index=False)
    elif format in ('hdf', 'hdf5'):
        df.to_hdf(fn, 'dataframe')
    elif format in ('pickle', 'pkl'):
        df.to_pickle(fn)
    elif format in ('excel', 'xls', 'xlsx'):
        if fn != filename and isinstance(fn, str) and fn.endswith('.excel'):
            fn = f'{filename}.xlsx'
        df.to_excel(fn, index=False)


def get_wow_path(tsm_log):
    tsm_log = Path(tsm_log)
    pattern = re.compile(r'.*WoW path is set to\s*(.*)\s*$', re.IGNORECASE)
    with tsm_log.open() as f:
        line = f.readline()
        while line:
            try:
                m = re.match(pattern, line)
                if m:
                    wow = m.group(1)
                    wow = wow.strip().strip("'").strip('"')
                    wow = Path(wow)
                    if wow.exists():
                        return wow
            finally:
                line = f.readline()


def get_tsm_log_path():
    tsm_log = os.path.expandvars(r'%APPDATA%\TradeSkillMaster\TSMApplication\TSMApplication.log')
    tsm_log = Path(tsm_log)
    return tsm_log


def main():
    tsm_log = None
    if platform.system() == 'Windows':
        tsm_log = get_tsm_log_path()
        if not tsm_log.exists():
            print("There's no TSM log.")
            tsm_log = None

    parser = argparse.ArgumentParser(description='extract tsm app data auctions.')
    parser.add_argument('-f', '--format', metavar='FORMAT', type=str, default='csv',
                        help='output file format', dest='format',
                        choices=('json', 'csv', 'pickle', 'hdf5', 'xlsx'))
    parser.add_argument('-r', '--app_helper_path', metavar='APP_PATH', type=str, required=tsm_log is None,
                        help='Path to AppData.lua', dest='app_helper_path')
    parser.add_argument('-o', '--output_dir', metavar='OUTPUT', type=str, default='.',
                        help='Path to output directory', dest='output_dir')

    args = parser.parse_args()
    if args.app_helper_path:
        for fn, df in iter_dataframes(args.app_helper_path):
            out = Path(args.output_dir, fn)
            export_dataframe(out, df, args.format)
    elif tsm_log:
        wow_path = get_wow_path(tsm_log)
        assert wow_path and wow_path.exists(), "unable to find wow directory." \
                                               " Please provide --app_helper_path command line argument"
        cnt = 0
        for wow_version in ('_retail_', '_classic_'):
            path = Path(wow_path, wow_version, r'Interface\AddOns\TradeSkillMaster_AppHelper\AppData.lua')
            if path.exists():
                print("processing %s version" % wow_version)
                for fn, df in iter_dataframes(path):
                    out = Path(args.output_dir, fn)
                    export_dataframe(out, df, args.format)
                    cnt += 1
        assert cnt > 0, "unable to locate any AppData.lua"
    else:
        assert Path(tsm_log).exists(), "TSM is not setup correctly"


if __name__ == '__main__':
    main()
