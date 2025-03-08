---
name: Bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

### 问题描述
请简要描述你遇到的问题。

### 步骤处理
请列出可出现问题的步骤：
1. ...
2. ...
3. ...

### 期望的结果
请描述你本应期望进程有什么表现。

### 实际的结果
请描述实际进程的表现。

### 环境信息
- 应用程序版本（使用/start查看）:

## （可选，提交时请删掉这一部分）如何收集日志

1. 请打开 `.env` 文件，将 `DEBUG` 设置为 `true`
2. 重启容器：
   ```sh
   docker-compose down && docker-compose up -d
   ```
3. 运行以下命令收集日志，并再次重复出现问题的操作：
   ```sh
   docker-compose logs -f
   ```
4. 如果你不确定哪部分日志有用，可以使用以下命令将日志存储到 `output.log`：
   ```sh
   docker-compose logs -f | tee output.log
   ```
5. 将目录下的 `output.log` 文件上传到 Issue。
