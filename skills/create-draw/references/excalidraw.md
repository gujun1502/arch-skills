# .excalidraw JSON 速查

drawkit.py 已封装全部写入逻辑，正常流程不需要手写 JSON。
本文档用于：调试生成的文件、解析用户手改的画布、或需要 drawkit 没有的元素类型时手工补。

## 顶层结构

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "create-draw-skill",
  "elements": [ ... ],
  "appState": { "gridSize": null, "viewBackgroundColor": "#FFFFFF" },
  "files": { "<fileId>": { "mimeType": "image/png", "id": "<fileId>",
             "dataURL": "data:image/png;base64,...", "created": 0, "lastRetrieved": 0 } }
}
```

Excalidraw 的 restore() 对缺字段宽容，会自动补默认值；但 drawkit 输出的字段集是
经过验证的安全集合，手工构造时照抄它的 `_base()`。

## 元素公共字段

`id, type, x, y, width, height, angle, strokeColor, backgroundColor, fillStyle,
strokeWidth, strokeStyle(solid|dashed|dotted), roughness, opacity(0-100), groupIds,
frameId, roundness, seed, version, versionNonce, isDeleted, boundElements, updated,
link, locked`

x/y 是元素包围盒左上角（不是圆心）。

## 分类型要点

- **ellipse / rectangle**：无额外字段。圆 = 包围盒为正方形的 ellipse。
- **line / arrow**：`points` 是相对 (x,y) 的坐标数组 `[[0,0],[dx,dy],...]`；
  arrow 另有 `startArrowhead / endArrowhead`（"arrow"|"bar"|"dot"|null）与
  `startBinding / endBinding`（不绑定就 null）。曲线用多点折线近似（drawkit 取 9 点）。
- **text**：`text, fontSize, fontFamily(1手写体 2普通 3代码), textAlign,
  verticalAlign, containerId, originalText, lineHeight(1.25)`。中文用 fontFamily 2。
  width/height 需自己估：CJK 字宽 ≈ fontSize，ASCII ≈ 0.55×fontSize。
- **image**：`status:"saved", fileId, scale:[1,1]`，图像数据放顶层 `files`，
  dataURL 必须带 `data:image/png;base64,` 前缀。
- **多边形填充**：type "line"，points 首尾闭合，`backgroundColor` 上色，
  `fillStyle:"hachure"` 即手绘风剖面线（"cross-hatch"、"solid" 也可）。

## 读回用户改动

`python drawkit.py info file.excalidraw` 会列出每个元素的类型/坐标/颜色语义。
注意：
- 用户拖动过的元素 `version` 会增大，但对我们只有最终坐标有意义；
- `isDeleted: true` 的元素是软删除，info 已过滤；
- 用户手画的笔迹是 `freedraw` 类型，points 很密，取首尾点和包围盒理解意图即可；
- 用户新画的形状颜色是 Excalidraw 默认色（#1e1e1e 等），不属于红蓝语义，
  按"用户指到了这里"理解位置，语义看他配的文字或对话。

## 打开方式（告诉用户）

- VS Code：装 "Excalidraw" 插件（pomdtr.excalidraw-editor），双击 .excalidraw 即开，
  画布就在 Claude Code 旁边，改完存盘即可让我 info 读回。
- 浏览器：excalidraw.com 直接拖文件进去。
