# Curly

Python Flask Micro movie website.


## 项目目录结构

```bash
$ tree ./
./
├── app                     # 项目APP
│   ├── admin               # 后台模块
│   │   ├── forms.py        # 表单处理文件
│   │   ├── __init__.py     # 初始化脚本
│   │   └── views.py        # 试图处理文件
│   ├── home                # 前台模块
│   │   ├── forms.py        # 表单处理文件
│   │   ├── __init__.py     # 初始化脚本
│   │   └── views.py        # 视图处理文件
│   ├── __init__.py         # 初始化文件
│   ├── models.py           # 数据模型文件
│   ├── static              # 静态目录
│   └── templates           # HTML模板目录
│       ├── admin           # 后台模板
│       └── home            # 前台模板
├── app.py
├── LICENSE
├── manager.py              # 入口启动脚本
├── README.md
└── requirements.txt

7 directories, 13 files
```