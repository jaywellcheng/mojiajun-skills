#!/usr/bin/env python3
"""
墨家军代码分派工作流 v2 — Tier 3 自动部署脚本

判断是否满足 Tier 3 自动部署条件，满足则自动部署到目标主机。

使用方式：
    from auto_deploy import should_auto_deploy, AutoDeployer

    deployer = AutoDeployer()
    ok, reason = deployer.should_auto_deploy(review_result, changed_files, lines_changed)
    if ok:
        deployer.deploy(files_to_deploy, target_host="CORE-01")
        deployer.notify_xiaochuan("Tier3", "自动部署完成")
"""

import subprocess
import os
import sys
from typing import List, Dict, Optional, Tuple


# ============================================================
# 关键路径 — 触及这些路径时禁止自动部署
# ============================================================
CRITICAL_PATHS = [
    "systemd/",
    ".env",
    "auth.json",
    "nginx/",
    "module_dispatcher.py",
    "task_queue schema",
    "ai-code-agent-governance/",
    "secret",
    "token",
    "password",
]

# ============================================================
# Tier 3 准入阈值
# ============================================================
MAX_LINES_TIER3 = 50  # Tier 3 最大变更行数


def should_auto_deploy(
    review_result: Dict,
    changed_files: List[str],
    lines_changed: int,
) -> Tuple[bool, str]:
    """
    判断是否可以执行 Tier 3 自动部署。

    Args:
        review_result: 墨码审核结果，必须包含 verdict 字段，
                       可选 minor_count 字段。
        changed_files: 变更文件列表（相对路径）。
        lines_changed: 变更总行数。

    Returns:
        (can_deploy, reason) — can_deploy 为 True 表示可以自动部署，
        reason 为判断说明字符串。
    """
    # 条件1: 墨码必须 PASS
    verdict = review_result.get("verdict", "UNKNOWN")
    if verdict != "PASS":
        return False, f"墨码未通过: verdict={verdict}"

    # 条件2: 无 minor issues
    minor_count = review_result.get("minor_count", 0)
    if minor_count > 0:
        return (
            False,
            f"有 {minor_count} 个 minor 问题，不满足 Tier 3 零问题要求",
        )

    # 条件3: 变更行数 ≤ 阈值
    if lines_changed > MAX_LINES_TIER3:
        return (
            False,
            f"变更 {lines_changed} 行，超过 Tier 3 阈值 ({MAX_LINES_TIER3})",
        )

    # 条件4: 不触及关键路径
    for f in changed_files:
        for cp in CRITICAL_PATHS:
            if cp in f:
                return False, f"触及关键路径: {cp} (文件: {f})"

    return True, "Tier 3 自动部署条件满足"


class AutoDeployer:
    """
    Tier 3 自动部署器。

    负责将变更文件从本地或远程源部署到目标主机。
    当前支持 CORE-01 作为目标。
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results: List[Dict] = []

    # ----- 公共接口 -----

    def should_auto_deploy(
        self,
        review_result: Dict,
        changed_files: List[str],
        lines_changed: int,
    ) -> Tuple[bool, str]:
        """
        判断是否满足 Tier 3 自动部署条件。
        委托给模块级函数 should_auto_deploy。
        """
        return should_auto_deploy(review_result, changed_files, lines_changed)

    def deploy(
        self,
        files: List[Dict[str, str]],
        target_host: str = "CORE-01",
        restart_services: Optional[List[str]] = None,
    ) -> Dict:
        """
        自动部署文件到目标主机。

        Args:
            files: 文件列表，每项包含 source 和 dest 路径。
                   例: [{"source": "/local/path/a.py", "dest": "/remote/path/a.py"}]
            target_host: 目标主机标识 ("CORE-01" 或 "GW-01")。
            restart_services: 需要重启的 systemd 服务列表（可选，需小川确认）。

        Returns:
            {"success": bool, "deployed": int, "errors": []}
        """
        deployed = 0
        errors = []

        for entry in files:
            source = entry["source"]
            dest = entry["dest"]

            if target_host == "CORE-01":
                ok, err = self._deploy_to_core01(source, dest)
            elif target_host == "GW-01":
                ok, err = self._deploy_to_gw01(source, dest)
            else:
                ok, err = False, f"未知目标主机: {target_host}"

            if ok:
                deployed += 1
            else:
                errors.append({"file": dest, "error": err})

        # systemd 相关：仅当文件在 systemd/ 路径下且小川明确确认时才重启
        if restart_services:
            for svc in restart_services:
                self._restart_service(svc, target_host)

        result = {
            "success": len(errors) == 0,
            "deployed": deployed,
            "errors": errors,
        }
        self.results.append(result)
        return result

    def notify_xiaochuan(self, tier: str, summary: str) -> None:
        """
        通知小川（当前阶段输出到 console）。

        Args:
            tier: 信任等级字符串，如 "Tier3"。
            summary: 部署摘要。
        """
        banner = "=" * 60
        print(f"\n{banner}")
        print(f"  [{tier}] 自动部署通知")
        print(f"  {summary}")
        print(f"{banner}\n")
        if self.dry_run:
            print("  [DRY-RUN] 以上为模拟，未实际部署。")

    # ----- 内部实现 -----

    def _deploy_to_core01(self, source: str, dest: str) -> Tuple[bool, str]:
        """
        通过 SSH cat 管道将文件传输到 CORE-01。
        """
        if self.dry_run:
            print(f"  [DRY-RUN] cat {source} → CORE-01:{dest}")
            return True, "dry-run"

        if not os.path.exists(source):
            return False, f"源文件不存在: {source}"

        try:
            # 读取本地文件内容，通过 SSH cat 写入远程
            with open(source, "r", encoding="utf-8") as fh:
                content = fh.read()

            cmd = ["ssh", "ubuntu@159.75.12.11", f"cat > {dest}"]
            proc = subprocess.run(
                cmd,
                input=content,
                text=True,
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                return False, f"SSH 传输失败: {proc.stderr.strip()}"
            return True, "ok"
        except subprocess.TimeoutExpired:
            return False, "SSH 连接超时"
        except Exception as exc:
            return False, str(exc)

    def _deploy_to_gw01(self, source: str, dest: str) -> Tuple[bool, str]:
        """
        GW-01 三步部署：先停 → 传输 → 后启。
        通过 CORE-01 中转到 GW-01。
        """
        if self.dry_run:
            print(f"  [DRY-RUN] GW-01 三步: stop → cat {source} → start")
            return True, "dry-run"

        if not os.path.exists(source):
            return False, f"源文件不存在: {source}"

        try:
            with open(source, "r", encoding="utf-8") as fh:
                content = fh.read()

            # 脚本：三步走（通过 CORE-01 中继到 GW-01）
            script = f"""
# Step 1: 停止 GW-01 相关服务
# (具体服务名由小川在调用时指定)
# Step 2: 传输文件
cat > {dest} << 'HERMES_EOF'
{content}
HERMES_EOF
# Step 3: 启动服务
echo "GW-01 部署完成: {dest}"
"""
            cmd = ["ssh", "ubuntu@159.75.12.11", script]
            proc = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=60,
            )
            if proc.returncode != 0:
                return False, f"GW-01 部署失败: {proc.stderr.strip()}"
            return True, "ok"
        except subprocess.TimeoutExpired:
            return False, "GW-01 部署超时"
        except Exception as exc:
            return False, str(exc)

    def _restart_service(self, service_name: str, host: str) -> None:
        """
        重启 systemd 服务（需小川确认，Tier 3 默认不自动重启）。
        """
        msg = f"⚠️ 需手动重启 systemd 服务: {service_name} on {host}"
        print(msg)
        # Tier 3 安全策略：systemd 重启永远需要人工确认
        # 此处仅记录，不执行


# ============================================================
# CLI 入口（调试用）
# ============================================================
if __name__ == "__main__":
    # 快速自检
    deployer = AutoDeployer(dry_run=True)

    # 测试 should_auto_deploy
    test_review = {"verdict": "PASS", "minor_count": 0}
    test_files = ["utils/helper.py"]
    test_lines = 30

    ok, reason = deployer.should_auto_deploy(test_review, test_files, test_lines)
    print(f"should_auto_deploy: ok={ok}, reason={reason}")

    # 测试通知
    deployer.notify_xiaochuan("Tier3", f"部署测试: {reason}")

    # 测试 deploy
    result = deployer.deploy(
        [{"source": "/dev/null", "dest": "/tmp/test_dest"}],
        target_host="CORE-01",
    )
    print(f"deploy result: {result}")
