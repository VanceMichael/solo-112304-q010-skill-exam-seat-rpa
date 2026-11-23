# 联合技能考核的实训机申领及双门户回填

学校归档授权与供应商机位租约分别登记。上传的文件为来自不同尝试的合成结果。

本地来源与合作端均使用合成业务资料。Python 3.11 运行来源服务，服务默认绑定回环地址。

```sh
python3 source_fixture.py --port 8765
python3 -m unittest discover -s tests -v
```

浏览器测试使用 Playwright 1.56.0 和随该版本安装的 Chromium。首次建立环境时运行 `python3 -m pip install -r requirements-browser.txt` 与 `python3 -m playwright install chromium`。

## 数据交换

- `/school/sessions` 链接两校的排考表。显示重复的题包名称不能证明同一供应对象，表中的题包指纹由 `/school/packages` 授权给指定学校与考段。
- `/school/submissions` 为考务提交范围，last 为闭区间最大上传序号，从 1 开始。archive 状态 verified 表示学校已确认，manual 表示考务已经正式接管。空值表示尚未完成。
- `/vendor/catalog` 提供供应商页面的实体机、镜像、当前盘世代和租用时限。用于新考段的物理机须独占并具备不同的干净盘世代。租约时间为同日北京时间。
- `/vendor/artifacts` 指向按尝试与临时盘组织的原件。missing 是来源确认找不到的序号。学校及供应商回填以当前业务号操作，逐行明细可写入所属考段、尝试、归档号、实训机和盘世代。

演练运维端 `GET /__scene` 返回当前时间点，`POST /__scene` 接受 JSON 字段 `index`，从 0 开始顺序切换，每次加 1。换场不会清除合作端当次运行已生成的回执。需要开始新的独立演练时重启服务。业务时间以各来源的当前版本为准。

合作端允许按 `request` 字段查找同路径下的业务请求号，提交使用 `request`、`operation`、`items`（字符串数组）。业务明细使用可选 JSON 对象 `details`，以此请求内的条目编号为键。界面端填多项时按逗号分隔。来源约定的业务动作按下表允许值填写。统一回执含请求号、模拟回执号与各行状态。相同请求号的原样重交返回原回执，参数有变则返回 HTTP 409。回执检索的 404 表示该时刻未查到。描述业务状态的可读来源会随演练进度独立更新，某次提交回执不会提前改写该来源。

## 合作端动作

- `/vendor/apply` 接受 `reserve`、`extend`、`release`。
- `/school/confirm` 接受 `writeback`、`archive`、`refer`。
