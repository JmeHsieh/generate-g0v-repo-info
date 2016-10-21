#!/usr/bin/env python3

from base64 import b64decode
import json
import logging
from os import listdir, makedirs
from os.path import abspath, dirname, isfile, join
from shutil import copy, rmtree
from subprocess import PIPE, Popen
from urllib.parse import urljoin, urlparse

from git import NoSuchPathError
from git.repo.base import Repo
from requests import get, Session


REQUIRED_KEYS = ['name', 'description', 'url', 'html_url', 'updated_at']
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    datefmt='%I:%M:%S %p')


def get_g0v_repos(session, info_path):
    info = {}
    url = 'https://api.github.com/orgs/g0v/repos?type=public'
    while url:
        response = session.get(url)
        url = response.links.get('next', {}).get('url', '')
        if response.status_code // 100 != 2:
            continue

        for repo in response.json():
            info[repo['full_name']] = {k: repo[k] for k in repo if k in REQUIRED_KEYS}

    with open(info_path, 'w') as f:
        logging.info('write g0v repos to repo_info.json')
        json.dump(info, f, sort_keys=True, ensure_ascii=False, indent=2)


def gen_awesome_list(output_dir):
    repo_raw = 'https://raw.githubusercontent.com/g0v/awesome-g0v/master/'
    readme_fn = 'readme.md'
    parser_fn = 'parse.ls'

    # get readme.md
    readme_url = urljoin(repo_raw, readme_fn)
    with open(join(output_dir, readme_fn), 'wb+') as f:
        response = get(readme_url)
        f.write(response.content)

    # get parse.ls
    parser_url = repo_raw + parser_fn
    with open(join(output_dir, parser_fn), 'wb+') as f:
        response = get(parser_url)
        f.write(response.content)

    # run parse.ls
    try:
        logging.info('generating awesome-g0v.json')
        with Popen(['lsc', parser_fn], cwd=output_dir, stdout=PIPE) as p:
            print(p.stdout.read().decode('utf-8'))
    except:
        pass


def get_awesome_repos(session, awesome_dir, info_path):
    gen_awesome_list(awesome_dir)

    with open(join(awesome_dir, 'awesome-g0v.json'), 'r') as f:
        awesome = json.load(f)
        awesome = [a['repository'] for a in awesome]

    with open(info_path, 'r') as f:
        info = json.load(f)

    for url in awesome:
        parsed = urlparse(url)
        fullname = parsed.path[1:]
        if fullname in info or 'github.com' not in parsed.netloc:
            continue

        api = parsed._replace(netloc='api.github.com', path=join('repos', fullname)).geturl()
        response = session.get(api)
        if response.status_code // 100 != 2:
            continue

        repo = response.json()
        info[repo['full_name']] = {k: repo[k] for k in repo if k in REQUIRED_KEYS}

    with open(info_path, 'w') as f:
        logging.info('write (g0v ∪ awesome) repos to repo_info.json')
        json.dump(info, f, sort_keys=True, ensure_ascii=False, indent=2)


def get_repo_languages(session, info_path):
    with open(info_path, 'r') as f:
        info = json.load(f)

    for fullname, repo in info.items():
        response = session.get(urljoin(repo['url'] + '/', 'languages'))
        if response.status_code // 100 != 2:
            continue
        repo.update({'languages': response.json()})

    with open(info_path, 'w') as f:
        logging.info('update languages to repo_info.json')
        json.dump(info, f, sort_keys=True, ensure_ascii=False, indent=2)


def get_repo_readmes(session, info_path, output_dir):
    with open(info_path, 'r') as f:
        info = json.load(f)

    for fullname, repo in info.items():
        response = session.get(urljoin(repo['url'] + '/', 'readme'))
        if response.status_code // 100 != 2:
            continue

        readme = response.json()
        if readme['encoding'] != 'base64':
            continue

        filename = '`'.join(fullname.split('/')) + '`' + readme['name']
        repo.update({'readme_filename': filename})

        content = b64decode(readme.get('content', '')).decode('utf-8')
        filepath = join(output_dir, filename)
        with open(filepath, 'w') as f:
            logging.info('write {}'.format(filename))
            f.write(content)

    with open(info_path, 'w') as f:
        logging.info('update readme filenames to repo_info.json')
        json.dump(info, f, sort_keys=True, ensure_ascii=False, indent=2)


def get_repo_g0vjsons(session, info_path, output_dir):
    with open(info_path, 'r') as f:
        info = json.load(f)

    for fullname, repo in info.items():
        response = session.get(urljoin(repo['url'] + '/', 'contents/g0v.json'))
        if response.status_code // 100 != 2:
            continue

        g0vjson = response.json()
        if g0vjson['encoding'] != 'base64':
            continue

        filename = '`'.join(fullname.split('/')) + '`' + 'g0v.json'
        repo.update({'g0vjson_filename': filename})

        content = b64decode(g0vjson.get('content', '')).decode('utf-8')
        filepath = join(output_dir, filename)
        with open(filepath, 'w') as f:
            logging.info('write {}'.format(filename))
            f.write(content)

    with open(info_path, 'w') as f:
        logging.info('update g0vjson filenames to repo_info.json')
        json.dump(info, f, sort_keys=True, ensure_ascii=False, indent=2)


def setup_bkrepo(repo_url, repo_path):
    try:
        repo = Repo(repo_path)
    except NoSuchPathError:
        logging.info('git clone: {}'.format(repo_url))
        repo = Repo.clone_from(repo_url, repo_path)
    else:
        logging.info('git pull: {}'.format(repo_url))
        repo.remote().pull()
    return repo


def copy_data(from_dir, to_dir):
    logging.info('copy data from {} to {}'.format(from_dir, to_dir))
    files = listdir(from_dir)
    for f in files:
        full_fn = join(from_dir, f)
        if isfile(full_fn):
            copy(full_fn, to_dir)


def commit_push(repo):
    if len(repo.index.diff(None)) == 0:
        logging.info('nothing to commit')
        return

    logging.info('git add .')
    repo.index.add('*')

    logging.info('changed files:\n{}'.format('\n'.join([d.b_path for d in repo.index.diff('HEAD')])))
    logging.info('git commit -m "commit updates."')
    repo.index.commit('commit updates.')

    logging.info('git push origin')
    repo.remote().push(repo.head)


def main():
    # prelude
    base_dir = dirname(abspath(__file__))
    data_dir = join(base_dir, '_data')

    awesome_dir = join(data_dir, 'awesome')
    makedirs(awesome_dir, exist_ok=True)

    temp_dir = join(data_dir, 'temp')
    makedirs(temp_dir, exist_ok=True)

    with open(join(data_dir, 'config.json'), 'r') as f:
        config = json.load(f)
        authtoken = config.get('token', '')
        bkrepo_url = config.get('backup_repo', '')
        bkrepo_name = urlparse(bkrepo_url).path.split('/')[-1].split('.')[0]
        if not authtoken or not bkrepo_url:
            raise Exception('Autoken / Repo not set in config.json')

    bkrepo_dir = join(data_dir, bkrepo_name)
    info_path = join(temp_dir, 'repo_info.json')

    # reuse session
    s = Session()
    s.headers.update({'Accept': 'application/vnd.github.v3+json'})
    s.headers.update({'Authorization': 'token %s' % authtoken})

    # fetch repo stuff
    get_g0v_repos(s, info_path)
    get_awesome_repos(s, awesome_dir, info_path)
    get_repo_languages(s, info_path)
    get_repo_readmes(s, info_path, temp_dir)
    get_repo_g0vjsons(s, info_path, temp_dir)

    # backup to bkrepo
    bkrepo = setup_bkrepo(bkrepo_url, bkrepo_dir)
    copy_data(temp_dir, bkrepo_dir)
    commit_push(bkrepo)

    # cleaning
    rmtree(awesome_dir)
    rmtree(temp_dir)


if __name__ == '__main__':
    main()
