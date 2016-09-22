# generate-g0v-repo-info
The running codes behind [g0v-repo-info](https://github.com/jmehsieh/g0v-repo-info)

# 目的
除了 `org: g0v` 底下的 repo 外，其他一些專案則是掛在作者的帳號下。目前雖然透過 [awesome-g0v](https://github.com/g0v/awesome-g0v) 人工蒐集主要的 repo 列表，但若需要所有 g0v repo 的資訊，都必須跑一次 (awesome-g0v + org: g0v) 的 repo api traversal。以 [search-g0v](https://github.com/g0v/search-g0v) 及 [issue_aggregator](https://github.com/g0v/issue_aggregator) 為例，都會需要所有 g0v 的專案資訊，透過單一的 [g0v-repo-info](https://github.com/JmeHsieh/g0v-repo-info) datasource, 可避免重複的工作。

# 設定 config.json
1. 將 `config_template.json` 拷貝到 `data/` 目錄下
2. 改名 `data/config_template.json` -> `data/config.json`
3. 在 config.json 中，`token` 填入自己的 github personal access token
4. 在 config.json 中，`backup_repo` 填入要備份到的 repo url

# 執行環境
```
# setup virtualenv
$ virtualenv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ python3 gen_repo_info.py
```

# 執行時間
根據 repo 數量多寡而定，目前約 350 個 repos, 總執行時間約為 4-5 分鐘。