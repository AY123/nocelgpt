# V2-017 工程验收

V2-017 CLOSED。受测代码`376ffae16921e07dc5202b429b0a3246c7e1d5a2`；[GitHub run43604282005](https://github.com/AY123/nocelgpt/actions/runs/43604282005)同SHA六门全部PASS：1558UNIT+244ARCH+231PG=**2033项，0失败/error/skip**。新58契约+15PG为子集。一次run/attempt1；六原ZIP的GitHub digest、source/run/driver/lock、命令退出/日志/产物hash及JUnit逐项核验。74文件inventory中14新增、2处仅追加PG覆盖，另58旧文件保持；旧Core/Canon/SQL/genre规则/锁不改。

正式能力：人工输入的Series/Arc/Chapter/Scene计划→确定性有限Contract，四种RequiredTransition复用原Delta及真实前值；冲突/保护/禁止/缺代价/未知输入给诊断而不改Canon。只读端口绑定已接受历史目标，不声称最新HEAD。真实前章原始UTF8/BOM/换行和末段hash绑定，第一章显式无前章，结束语义允许UNKNOWN。错误Belief不升级Knowledge，安静/认知章节无需强制变化；场景约束保留局部作用域。

计划版本/采用边及冻结输入保持完整，冻结还覆盖父卷/全局意图；合法未来修订和有范围失效需显式采用后重编译，不自动重规划。人工初始知识与当前parent绑定的KnowledgeSnapshot分开，不改root冒充知识更新。合约保留完整PlanHistory/Pack/知识/接续及只读Canon投影，作者输入标AUTHOR_REVIEW_ONLY。前章投影不嵌套旧合约/Context，30次组件编译体积有界不冒充30章认证；完整原章依赖仍在Canon。

实际Owner在本对话采用OWNER_REVIEW.md的两份完整开发输入，hash f1029cf8456a5332172bb4abe430922f19e7a990a656bafa01ce6a97b3776c3d；OWNER_DECISION.json记录实际回答，原DRAFT不倒写。类型化《灯下机床》《断脉渡》包含初始事实/选择代价/错误信念及知情/揭示边界，source/derived hash及真实PG根初始化核验，AT04不使用合成APPROVED代替人类。

首轮组件44PASS/2FAIL为新视图错误比较合法root列表顺序；改完整snapshot-map验证，新视图往返及全部数据断言保留，原Canon格式未改。最终只使用本次同SHA远程结果。54安全finding仍OPEN且54/54精确消费，0新增未匹配/过期/未消费，51依赖0漏洞。同操作者实施/技术交叉检查，不称独立人员审核。

## 边界

当前仅既有标量事实及两个已注册扩展，不增加事件/知识/Promise Canon写操作。知识与结束语义为显式输入，不证明全文抽取/Q2/Q3、生产Permit、自然写作、阅读/市场质量或外部备份。PlanHistory/CanonView是显式冻结输入；调用方须提供当前版本，本库不声称已实现全局规划数据库或最新HEAD认证。没有Writer/Context/Gateway/持久Workflow。双书是人工采用的开发fixture，不是已生成/读者认可的长篇成稿。

P4/G-P4工程结项复用本次结果，不运行额外CI；M4单章端到端仍待P7。下一任务V2-018 Context Compiler，须先处理ADR009并按角色筛选AUTHOR_REVIEW_ONLY来源。
