# 设置界面优化清单（方案 B：可靠性 + 易用性小修）— 已审核，待实施

范围原则：**只改两个前端 HTML 文件**（web_config.html / macro_editor.html），不改后端 py；不引入任何外部资源；新增内联 JS/CSS 预算 ≤ 3KB。视觉体系（GitHub 暗色变量）保持不变。

> 审核修订记录（本轮）：R1 的 fetch 数量、R1 的 apiFetch 设计、R2 的现状措辞、R3 的反例均按真实代码更正。O1/O2 维持默认（O1 不做、O2 保留）。

---

## 一、可靠性修复（5 项）

### R1. 统一请求封装 apiFetch()【两页都改】

**现状**：共 **8 处**裸 `fetch()`（web_config.html 4 处：L66 初始 GET、L107 save POST、L111 reboot 里的 POST settings + POST /api/reboot；macro_editor.html 4 处：L106 初始 GET、L113 GET /api/macro、L282 save 外层 GET、L286 POST），全部不检查 `r.ok`；失败时用户看到 `Error: TypeError: JSON Parse error` 天书；无超时，设备忙时页面假死。

**修改**：新增公共函数（每页各内联一份），**带 `noJson` 开关**：

```js
function apiFetch(url, opts, noJson){
  opts = opts || {};
  return new Promise(function(res, rej){
    var t = setTimeout(function(){ rej(new Error('Timeout')) }, 8000);
    fetch(url, opts).then(function(r){
      clearTimeout(t);
      if(!r.ok) throw new Error('HTTP ' + r.status);
      return noJson ? r : r.json();
    }).then(res).catch(function(e){ clearTimeout(t); rej(e); });
  });
}
```

6 处**消费返回体的**调用全部替换为 `apiFetch`，错误统一走 `msg(e.message, 'err')`。

**reboot / 探针不要用 json 强约束**：`POST /api/reboot` 设备会立刻重启、响应常常拿不到；若走强制 `r.json()` 会卡在 8 秒 Timeout 而**误报失败**（其实重启已成功）。reboot 发送与 U3 的存活探针一律传 `noJson=true`（只判 HTTP 状态/能否连通），或在探针里用 `noJson` 拿到 Response 后自行 `.json()` 再判断。

**风险**：低。**验证**：拔网线/停服务后点 Save，8 秒内出现"Timeout"提示；点 Save & Reboot 不因 reboot 响应超时而误报错误。

### R2. 保存失败不再重启【web_config.html · reboot()】

**现状**：`reboot()` 只在 POST /api/settings **网络失败**（reject）时才进 catch 不重启；但只要后端返回 200 而 `ok:false`（保存被校验拒绝），`.then` 链会照样直接 POST /api/reboot。真正的缺口是**不检查 `d.ok`** → "没保存成功→重启→改动全丢"。

**修改**：保存返回成功（解析后 `d.ok` 为真）才发 reboot；否则显示后端错误并**中止**，附文案 "Save failed, reboot aborted"。

**风险**：低。**验证**：后端模拟保存失败（`ok:false`），确认设备不重启。

### R3. 提交前输入校验【web_config.html · getCfg()】

**现状（按真实代码更正）**：[getCfg()](file:///l:/git/blekey-8bit/web_config.html#L86-L92) 用 `+value` 转换。
- pin 留空 → `+""` 在 JS 里是 **`0`，不是 `NaN`/`null`**，结果是**静默把按键改成 GPIO0**（比变 null 更危险，直接占用真实引脚）。
- `trigger_pins` 输入 `0, ` → `["0"," "]` → `+"".trim()` → **`[0, 0]`**（不是 `[0, NaN]`）。
- `NaN` 只在输入**非数字**（如 `abc`）时才出现，序列化后变 `null`。
共性问题：无任何前端校验，空/非数字都会污染配置（后端虽容错，但坏数据已入库，且"空→0"这条路径后端也救不回来）。

**修改**：`save()`/`reboot()` 提交前统一过 `validate()`：
- 每个 Button 行：pin 输入框**先判空**（`trim()===''` 直接报错，堵住"空→0"），再要求为 ≥0 整数，否则 `msg('Button N: invalid pin', 'err')` 并中止
- trigger_pins：按逗号拆分 → 逐项 `trim()` 过滤空项 → 余下每项必须为 ≥0 整数（非数字报错），过滤后全空则报错
- long_press_ms / web_port：非空正整数；web_port 范围 1~65535
- 校验通过的行标绿边框，失败的行标红边框，错误消息指明第几个 Button

**风险**：低。**验证**：pin 留空点 Save → 红色边框 + "Button 1: invalid pin"，网络面板无 POST；trigger 输入 `0, ` → 得到 `[0]`（空项被过滤、不报错）；trigger 输入 `abc` → 报错。

### R4. 编辑器补全错误处理【macro_editor.html · saveMacro() / 初始化】

**现状**：`saveMacro()` 外层 GET 无 catch；页面初始化的 GET 也无 catch——失败纯静默，用户对着空白事件列表发呆。

**修改**：两处外层 fetch 换 `apiFetch` 并 `.catch(e => msg(...))`；保存成功后按钮短暂禁用防双击重复提交。

**风险**：低。**验证**：设备端手工制造 500，编辑器保存时能看到具体错误。

### R5. 保存按钮防重入 + 消息自动消失【两页】

**现状**：Save 连点会并发 POST 两次；"Saved OK" 永驻，无法区分是这次还是上次的结果。

**修改**：提交期间禁用 Save 按钮（文案变 "Saving..."），完成后恢复；`msg()` 成功消息 3 秒自动隐藏，错误消息保留至下次操作。

**风险**：低。**验证**：快速双击 Save，网络面板只有一次 POST；成功提示 3 秒后消失。

---

## 二、易用性改进（4 项）

### U1. 按键行加标题 + DISABLED 禁入编辑器【web_config.html · render()】

**现状**：按键行只有 pin 框 + 宏下拉，无 "Button N" 标识；DISABLED 按键也能点 ✎ 进编辑器，保存后意外变成 CUSTOM。

**修改**：
- 每行左侧加固定宽度的 `Button N` 文本标签
- `macro === 'DISABLED'` 时 ✎ 按钮置灰 `disabled`，title 提示 "Enable a macro first"

**风险**：低。**验证**：DISABLED 行 ✎ 不可点；行首有 Button 1/2 标签。

### U2. 未保存修改守卫【两页】

**现状**（最痛的丢数据场景）：主页改了下拉框不点 Save 直接进编辑器 → 丢；编辑器编辑一半点 Back → 丢；全程零提示。

**修改**：
- 两页给所有 input/select/checkbox 挂 `change` 监听置 `dirty = true`，Save 成功后清 false
- `window.onbeforeunload = dirty ? 'Unsaved changes' : null`（管住刷新/关标签页）
- 主页 ✎ 点击、编辑器 Back 按钮：`dirty` 时 `confirm('Unsaved changes, leave anyway?')`

**风险**：低（onbeforeunload 浏览器原生弹窗，无法自定义文案样式，可接受）。**验证**：改一个下拉不保存 → 点 ✎ 弹确认框；取消后可继续编辑并保存。

### U3. 重启全流程反馈【web_config.html · reboot()】

**现状**：点 Save & Reboot 后设备离线约 10 秒，页面毫无反应，用户以为死机重复点击。

**修改**：
1. 保存成功、reboot 请求发出后：绿色提示 "Rebooting, waiting for device…"，禁用两个按钮
2. 每 2 秒轮询 `GET /api/settings`（探针，最多 60 秒）
3. 探针成功 → 提示 "Device is back" → 1 秒后 `location.reload()`
4. 超时 → 提示 "Device not reachable after 60s, check the IP and refresh manually"

**风险**：低；轮询间隔 2s 不会触发 MAX_CLIENTS/内存护栏。**验证**：真机走一遍，看到完整三段反馈且页面自动恢复。

### U4. 编辑器目标按键回显【macro_editor.html】

**现状**：编辑器只显示 `Button #N (Pin X)`，看不出编辑的宏当前是什么类型；单键宏被展开成事件后用户不知道"保存就变 CUSTOM"。

**修改**：`btn-info` 行追加当前宏名，如 `Button #1 (Pin 0) — macro: W_SWITCH`；当原宏非 CUSTOM 时，事件列表上方加一行灰字提示 "Saving will convert this button to a CUSTOM macro"。

**风险**：低。**验证**：从 W_SWITCH 按键进编辑器，能看到宏名与转换提示。

---

## 三、可选项处理结论（本轮已拍板）

### O1. 编辑器竞态覆盖（需改后端）—— **本轮不做**

**问题**：编辑器保存是"读整个 settings → 改一格 → 写回整个 settings"，与主页并发保存时后写覆盖先写。前端无法根治。
**彻底方案**：web_config.py 新增 `POST /api/button/<idx>` 只更新单个按键（后端合并），编辑器改调它。改动约 30 行 Python + 10 行 JS。
**结论**：单人单页面操作触发概率很低，**本轮维持不做**（已确认）。

### O2. delay 事件类型 —— **保留不动**

编辑器下拉里的 `delay` 类型对应后端真实的 `DelayEvent`（CTRL combos、WHEEL_CLICK 等内置宏在用），**不是冗余**，本次清单不动它（已确认）。

---

## 四、改动量与回归预算

| 文件 | 预计增量 | 改动点 |
|---|---|---|
| web_config.html | +约 2KB | apiFetch、validate、dirty 守卫、reboot 轮询、Button 标签、msg 自动消失 |
| macro_editor.html | +约 1KB | apiFetch、dirty 守卫、Back 确认、宏名回显、防重入 |

## 五、上机回归清单（改完后逐项过）

1. 正常流程：主页改 pin/宏 → Save → 3 秒提示消失 → 数据落盘
2. 主页改下拉不保存 → 点 ✎ → 弹确认；取消 → 继续保存成功
3. DISABLED 行 ✎ 置灰不可入
4. pin 留空 / pin 输入 `abc` → 红色标行 + 指名 Button N，无 POST 发出；trigger 输入 `0, ` → 存为 `[0]`（空项过滤，不报错）；trigger 输入 `abc` → 报错
5. 编辑器改事件 → Back → 弹确认
6. 编辑器从 W_SWITCH 进入 → 显示宏名 + CUSTOM 转换提示 → 保存生效
7. Save & Reboot → "Rebooting…" → 设备回来后自动刷新
8. 拔网线点 Save → 8 秒内 Timeout 提示，页面不假死
9. 快速双击 Save / 保存按钮 → 网络面板仅一次 POST
10. 全部正常后：配置模式整体加载时间肉眼对比（应无感）
