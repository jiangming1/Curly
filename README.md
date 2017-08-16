# Curly

Python Flask Micro movie website.

## Directory Structure

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
├── README.md               # 帮助文档
└── requirements.txt        # Python所需要的安装包

7 directories, 13 files
```

## Run MySQL

- Download the MySQL image

```bash
$ sudo docker pull mysql
```

- Start the MySQL container

```bash
$ sudo docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=123456 -e MYSQL_DATABASE=curly -p 3306:3306 mysql
```

## Run Redis

- Download the Redis image

```bash
$ sudo docker pull redis
```

- Start the Redis container

```bash
$ sudo docker run --name redis -d -p 6379:6379 redis
```