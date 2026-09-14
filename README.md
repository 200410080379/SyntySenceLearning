# SyntySenceLearning

用于学习、复现和验证 Synty 场景搭建的长期仓库。按资源包保存研究笔记、最小拼接样板、独立训练布局、构建脚本、实测报告和 UE 截图，逐步积累可复用的搭建方法。

首批内容研究 **POLYGON Apocalypse** 的城市地面：先确认模块接口，验证 80×80 米连续地面，再扩大到 200×160 米，学习主街、支路、不同区域和出入口的关系。

![仓库脚本重建的城市地面](packs/polygon-apocalypse/studies/02-city-ground/Screenshots/Repository_CityGround_Reproduction.png)

## 学习目录

| 资源包 | 训练 | 主要内容 |
| --- | --- | --- |
| [POLYGON Apocalypse](packs/polygon-apocalypse/README.md) | [01 原包地面拼接](packs/polygon-apocalypse/studies/01-ground-assembly/README.md) | 30 个学习实例；原样与拆开对照、路缘、转角和入口 |
| POLYGON Apocalypse | [02 城市地面验证](packs/polygon-apocalypse/studies/02-city-ground/README.md) | 256 块地面、十字路、环路、街角、斑马线和院落入口 |
| POLYGON Apocalypse | [03 扩大街区](packs/polygon-apocalypse/studies/03-expanded-neighborhood/README.md) | 1,280 块地面、错位 T 字路口，以及加油站、饭店、旅馆等区域预留 |

第二课的历史实测结果为 **480 条相邻接缝通过 1 mm 高差阈值检查**，并完成保存重开与近远景观察。该结果针对当时的模型版本、布局和几何算法；新环境需要重新验证，不包含角色碰撞或导航验收。

仓库整理后的脚本也已在 UE 5.8.2 中实际重建两课：使用独立资产目录，30 个学习实例和 256 块城市地面的保存重开检查均通过，480 条接缝重新计算通过。结果分别见[第一课复现记录](packs/polygon-apocalypse/studies/01-ground-assembly/Data/ReproductionValidation.json)和[第二课复现记录](packs/polygon-apocalypse/studies/02-city-ground/Data/ReproductionValidation.json)。本次复现使用已安装所需资源的现有工程，未测试全新引擎安装。

第三课保留原测试场景，在独立关卡中将地面面积扩大为 5 倍，重新检查的 2,488 条相邻接缝通过，1,280 个实例保存重开后的只读核对零失败，见[第三课验证记录](packs/polygon-apocalypse/studies/03-expanded-neighborhood/Data/ReproductionValidation.json)。区域用途用于组织地面、入口和前后场，建筑尺寸、碰撞、导航及完整玩法尚需分区域验证。

## 在自己的 UE 工程复现

需要本地拥有并安装对应资源包。首批训练使用 `/Game/PolygonApocalypse` 下的原始资产，研究版本为 POLYGON Apocalypse v1.20.0（UE 5.3 资源），历史验证环境为 UE 5.8.2。

1. 在 UE5 工程中启用 **Python Editor Script Plugin** 和 **Editor Scripting Utilities**，按编辑器提示重启。
2. 将已授权使用的资源包放入工程，保持 `/Game/PolygonApocalypse` 引用路径及原始资产不变。
3. 在仓库根目录运行下列命令，将示例路径替换为自己的 `.uproject` 绝对路径。

```powershell
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study ground-assembly
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study city-ground
python tools/prepare_study.py --project "X:/YourProject/YourProject.uproject" --study expanded-neighborhood
```

准备工具将训练文件放入工程的 `Learning/SyntySenceLearning/polygon-apocalypse/<study-id>`，并输出实际执行入口及 MCP 所需的工程相对路径。随后在打开该工程的 UE 中执行对应 Python 文件；已有可用 MCP 时可使用其 Python 执行能力，也可以直接使用 UE 的 Python 文件执行功能。

生成的学习资产分别位于 `/Game/SyntySenceLearning/PolygonApocalypse/` 下的 `GroundAssembly`、`CityGround` 与 `ExpandedNeighborhood` 独立目录。仓库不依赖最初的 JSQS 工程，也不捆绑 MCP 服务。不同 UE 或资源包版本的复现结果应另行记录。

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
