# SyntySenceLearning

用于学习、复现和验证 Synty 场景搭建的长期仓库。按资源包保存研究笔记、最小拼接样板、独立训练布局、构建脚本、实测报告和 UE 截图，逐步积累可复用的搭建方法。

首批内容研究 **POLYGON Apocalypse** 的城市区域：先确认地面模块接口，验证 80×80 米连续地面，再扩大到 200×160 米，学习主街、支路和出入口的关系；随后加入建筑，并从真实节点学习道具组合、自然侵入、旧化和外围林缘，发展成独立的末日小城。

![仓库脚本重建的城市地面](packs/polygon-apocalypse/studies/02-city-ground/Screenshots/Repository_CityGround_Reproduction.png)

## 学习目录

| 资源包 | 训练 | 主要内容 |
| --- | --- | --- |
| [POLYGON Apocalypse](packs/polygon-apocalypse/README.md) | [01 原包地面拼接](packs/polygon-apocalypse/studies/01-ground-assembly/README.md) | 30 个学习实例；原样与拆开对照、路缘、转角和入口 |
| POLYGON Apocalypse | [02 城市地面验证](packs/polygon-apocalypse/studies/02-city-ground/README.md) | 256 块地面、十字路、环路、街角、斑马线和院落入口 |
| POLYGON Apocalypse | [03 扩大街区](packs/polygon-apocalypse/studies/03-expanded-neighborhood/README.md) | 1,280 块地面、错位 T 字路口，以及加油站、饭店、旅馆等区域预留 |
| POLYGON Apocalypse | [04 建筑装配与摆放](packs/polygon-apocalypse/studies/04-building-placement/README.md) | 10 套装配配方、13 栋主建筑和 1 组加油棚；在第三课地图中添加 94 个部件 |
| POLYGON Apocalypse 与 Woodland 参考 | [05 末日小城](packs/polygon-apocalypse/studies/05-aftermath-town/README.md) | 5,053 个模型实例、184 个贴花、11 个机位；主图与独立完整复现副本均保存重开、实例核对零错误 |
| POLYGON Apocalypse 与 Woodland 参考 | [06 末日街道切片](packs/polygon-apocalypse/studies/06-street-slice/README.md) | 真实 Landscape、1,206 个模型实例和 35 个贴花；保存重开核对零错误，含指定地面射线与胶囊扫掠检查 |

第二课的历史实测结果为 **480 条相邻接缝通过 1 mm 高差阈值检查**，并完成保存重开与近远景观察。该结果针对当时的模型版本、布局和几何算法；新环境需要重新验证，不包含角色碰撞或导航验收。

仓库整理后的脚本也已在 UE 5.8.2 中实际重建两课：使用独立资产目录，30 个学习实例和 256 块城市地面的保存重开检查均通过，480 条接缝重新计算通过。结果分别见[第一课复现记录](packs/polygon-apocalypse/studies/01-ground-assembly/Data/ReproductionValidation.json)和[第二课复现记录](packs/polygon-apocalypse/studies/02-city-ground/Data/ReproductionValidation.json)。本次复现使用已安装所需资源的现有工程，未测试全新引擎安装。

第三课保留原测试场景，在独立关卡中将地面面积扩大为 5 倍，重新检查的 2,488 条相邻接缝通过，1,280 个实例保存重开后的只读核对零失败，见[第三课验证记录](packs/polygon-apocalypse/studies/03-expanded-neighborhood/Data/ReproductionValidation.json)。区域用途用于组织地面、入口和前后场，建筑尺寸、碰撞、导航及完整玩法尚需分区域验证。

第四课沿用第三课地图和地面布局，记录主体、玻璃、独立门枢轴、镜像及附件的关系，再把局部装配用于四个街块。建筑主体和加油棚保留原始尺寸，门和招牌保留测得的原配方缩放；验证建筑实例与原地面摆放，具体结果及限制见[第四课说明](packs/polygon-apocalypse/studies/04-building-placement/README.md)。

第五课在独立关卡中组织加油站、饭店、旅馆、维修院与商铺，保留约 200×160 米核心街区并补充道路延伸、森林与山体。研究以模型节点、父子变换、实例材质和几何测量为先，截图用于画面验收。主图与从空图完整构建的副本均完成保存重开和只读核对；地面碰撞检查保留了 11 个复杂碰撞接缝未命中，并另做偏移复查。当前部分空地较大、模块排列较规整，美术密度仍可深化；没有有效性能采样，尚未导航、玩法和打包验收。具体证据见[第五课说明](packs/polygon-apocalypse/studies/05-aftermath-town/README.md)。 饭店西侧与旅馆东侧另增 158 个模型实例和 12 个贴花，形成连续植被带，原有 456 个内部自然侵入实例保留。

## 在自己的 UE 工程复现

需要本地拥有并安装对应资源包。第 1–5 课的 Apocalypse 主资源使用 `/Game/PolygonApocalypse` 下的 v1.20.0（UE 5.3 资源），历史验证环境为 UE 5.8.2。第六课使用 Apocalypse 1.21.1、Woodland 1.0.0 和 Alpine Mountain 1.1.0 的 `/Game/Synty/...` 路径，并需通过原生 Landscape 界面创建真实地形组件；请按[第六课说明](packs/polygon-apocalypse/studies/06-street-slice/README.md)准备其版本与复现前置条件。

1. 在 UE5 工程中启用 **Python Editor Script Plugin** 和 **Editor Scripting Utilities**，按编辑器提示重启。
2. 将已授权使用的资源包放入工程，保持各课要求的引用路径及原始资产不变；第 1–5 课的 Apocalypse 主资源使用 `/Game/PolygonApocalypse`，第六课使用上述 `/Game/Synty/...` 路径。
3. 在仓库根目录运行下列命令，将示例路径替换为自己的 `.uproject` 绝对路径。

```powershell
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study ground-assembly
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study city-ground
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study expanded-neighborhood
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study building-placement
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study aftermath-town
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study street-slice
```

准备工具将训练文件放入工程的 `Learning/SyntySenceLearning/polygon-apocalypse/<study-id>`，并输出实际执行入口及 MCP 所需的工程相对路径。随后在打开该工程的 UE 中执行对应 Python 文件；已有可用 MCP 时可使用其 Python 执行能力，也可以直接使用 UE 的 Python 文件执行功能。

前三课生成的学习资产分别位于 `/Game/SyntySenceLearning/PolygonApocalypse/` 下的 `GroundAssembly`、`CityGround` 与 `ExpandedNeighborhood` 独立目录。第四课依赖第三课，直接在其 `L_ExpandedNeighborhood` 地图中添加建筑；准备工具不会自动构建前置训练，需要按两课步骤顺序执行。第五课在 `AftermathTown` 下建立独立地图，使用自带最终布局，另需按该课依赖清单准备 Woodland、PolygonGeneric 和指定 Alpine/Biomes 资源。仓库不依赖最初的 JSQS 工程，也不捆绑 MCP 服务。不同 UE 或资源包版本的复现结果应另行记录。

## 仓库结构

```text
packs/
  <pack-id>/
    README.md
    studies/
      <study-id>/
        README.md
        Data/          # 精简布局、接口分析与验证记录
        Scripts/       # 本地构建、测量和验证脚本
        Screenshots/   # 实际 UE 观察证据
docs/WORKFLOW.md        # 从原场景研究到保存重开的工作流
templates/study/        # 新训练的说明与元数据模板
tools/                 # 准备训练文件等公共工具
AGENTS.md              # 协作约定
```

新增资源包时创建独立的 `packs/<pack-id>`，新增练习时创建独立的 `studies/<study-id>`。根目录 `catalog.json`、资源包 `pack.json` 和训练 `study.json` 负责登记依赖及执行入口。具体记录方式见[工作流](docs/WORKFLOW.md)和[训练模板](templates/study/README.md)。

## 文件边界

仓库保存学习方法和可复现的摆放配方。原始 `.uasset` / `.umap`、完整网格几何导出、原贴图、完整源 Demo 布局、构建缓存、日志及私有数据留在本地。构建脚本通过资产路径引用本地资源，运行时生成的关卡和派生材质保存在使用者自己的工程中。

截图和历史报告保留研究时的真实结果；它们与重新生成的结果分别记录。资源包本身仍按其原有授权使用，本仓库不提供或授予原资源的使用权。
