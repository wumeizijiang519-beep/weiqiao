# 魏桥服务器关停记录：Simple-WAM Visual RL/QGF

记录日期：2026-10-31（Asia/Shanghai）

## 本地保留内容

主要记录目录：

- `D:/qgf_evidence/simplewam_visual_rl_v1_shutdown_record_20261031`
- `C:/Users/SEU student/Documents/Codex/2026-07-10/new-chat/server_backup_2026-10-31/evidence_snapshot`

本地实际保留的是文字、源码与小型证据：

- `simplewam_text_source_records_20261031.tar.gz`，3,264,860 bytes。
- 源码记录包 SHA256：`5268558a62baa8c3d6b4aa54dd4c708f273b76f32df1bbca707b0a0b7c14ea88`，已完成服务器/本地一致性校验。
- 530项紧凑源码/协议/注册/审计/环境记录。
- 最终formal报告、独立审计、协议、状态和handoff的直接可读快照。
- D盘原有的小型报告和final critic证据继续保留；没有新增大模型副本。

## 未下载的大文件

以下文件因用户要求“不要备份太多、容量大的checkpoint不要下载”而只记录元数据，不在本地保存：

| 资产 | 服务器原路径 | 大小（bytes） | SHA256 |
|---|---|---:|---|
| OpenWAM LIBERO checkpoint | `/public/wangsenbao221/pqr/qgf_mainstream_20261022/checkpoints/OpenWAM-Alpha-Sim-LIBERO/checkpoint_step_10690.safetensors` | 24,813,767,464 | `34c9a6c9af67dda9aaffa2edc0efa29b28eeee1c26dea419f98065c80508c96a` |
| Wan2.2 VAE | `/public/wangsenbao221/pqr/qgf_mainstream_20261022/checkpoints/UniWAM-Wan2.2-TI2V-5B/Wan2.2_VAE.pth` | 2,818,839,170 | `20eb789667fa5e60e7516bf509512f6cb61f01b0aa0695eadaea930c13892b36` |
| UMT5-XXL encoder | `/public/wangsenbao221/pqr/qgf_mainstream_20261022/checkpoints/UniWAM-Wan2.2-TI2V-5B/models_t5_umt5-xxl-enc-bf16.pth` | 11,361,920,418 | `7cace0da2b446bbbbc57d031ab6cf163a3d59b366da94e5afe36745b746fd81d` |
| RL token checkpoint | `/public/wangsenbao221/pqr/qgf_mainstream_20261022/simplewam_visual_rl_v1/token_training_v1/TOKEN.pt` | 889,863,915 | `40a436a09e618965642f680bda5d1339f3426ccd735b73aba6629fbbc46a8c97` |
| Critic corpus | `/public/wangsenbao221/pqr/qgf_mainstream_20261022/simplewam_visual_rl_v1/critic_corpus_v1/CORPUS.npz` | 94,934,614 | `a2337827258238d6369a0161179491ffe3629b04f113cea9c0ab3d84a56e62b0` |

未保存的其他大内容：12506条视觉特征、逐步NPZ trace、视频、Python虚拟环境、编译缓存、旧实验runs和历史大型checkpoint。

此前生成的约919 MiB归档和D盘849 MiB `TOKEN.pt`副本已按用户要求从本机移除，不再占用空间。其旧清单与旧SHA文本仅作为“曾核验但未保留”的记录。

## 可恢复版本信息

- 主干：冻结Simple-WAM LIBERO视觉/动作生成器 -> outcome-blind RL token -> TwinQ/IQL -> rerank/QGF。
- Simple-WAM源码目录版本标识：`Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a`。
- OpenWAM公开项目：`https://github.com/OpenWAM-Official/OpenWAM`。
- OpenWAM模型名：`OpenWAM-Alpha-Sim-LIBERO`。
- backbone配置、requirements、运行脚本、pip freeze、Python/系统版本、模型路径与文件清单均在3.2 MB源码记录包中。
- LIBERO BDDL/init正文未复制；其精确路径和场景选择保留在formal注册及源码记录中，可从公开LIBERO依赖恢复。

关键数据证书：

- `COHORT_MANIFEST.json` SHA256：`7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9`。
- `DATASET_RESULT.json` SHA256：`baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87`。
- `EXPERIMENT_MANAGEMENT.md` SHA256：`31d145e17b4a4f49ac147d77cecb27bbf25c2f597c7320223f4a3fdba262d499`。

## 冻结实验结论

- Full-data final critic：三个固定seed各50000 updates，独立审计PASS。
- Untouched formal：103个物理组、412/412任务、FAILED=0，独立审计PASS。
- 成功率：candidate0 74.76%，uniform random 76.70%，critic rerank 71.84%，visual QGF 73.79%。
- visual QGF相对candidate0为-0.97个百分点，相对uniform random为-2.91个百分点，95% bootstrap区间均跨0。
- 冻结状态：`NO_SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_BENEFIT`。
- 最终报告SHA256：`ab8ffbd1dafabc4e2493ed867d14a7759e27f71a5614c8782f2446ebf6fca86d`。
- 独立审计报告SHA256：`a14cec408f44a99c048615f46a4e621e7f8641a46ac2f2505afeaec234a76d73`。

## 能与不能恢复的范围

这份记录足以：

- 审计研究路线、预注册、训练合同、场景选择和最终结论。
- 恢复项目自写源码与配置。
- 用哈希核对未来重新下载的公开WAM依赖是否与原实验一致。

这份记录不能离线独立完成端到端复跑，因为大模型权重、RL-token权重、视觉特征和运行环境本体未保存。这是为满足“不占满本地电脑、不备份大checkpoint”所做的明确取舍，而不是遗漏。
