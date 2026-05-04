        # === 工作流回退 hook — 审核驳回自动生成重写任务 ===
        try:
            task_type = task.get('task_type', '') if task else ''
            # 仅对审核类任务触发回退逻辑
            if task_type in ('quality_audit', 'pre_publish_check'):
                module_result = result.get('module_result', {})
                if isinstance(module_result, str):
                    import json as _json
                    try:
                        module_result = _json.loads(module_result)
                    except Exception:
                        module_result = {}
                
                # 判断是否驳回（兼容多种返回格式）
                audit_passed = True
                if isinstance(module_result, dict):
                    audit_passed = module_result.get(
                        'passed',
                        module_result.get('audit_result', {}).get('passed', True)
                    )
                
                if not audit_passed:
                    import uuid as _uuid
                    import pymysql as _pymysql
                    import json as _json2
                    
                    # 提取驳回意见
                    feedback = module_result.get(
                        'feedback',
                        module_result.get('issues', module_result.get('suggestions', '请修改后重新提交'))
                    )
                    if isinstance(feedback, list):
                        feedback = '; '.join(str(f) for f in feedback)
                    
                    # 当前重试次数
                    retry_count = task.get('retry_count', 0)
                    
                    # 熔断：连续驳回3次不再重试
                    if retry_count >= 3:
                        logger.warning(
                            '🛑 %s 已连续驳回%d次，熔断！需人工介入。反馈：%s',
                            task.get('task_id', '?'), retry_count, feedback
                        )
                    else:
                        rework_task_id = _uuid.uuid4().hex[:8]
                        rework_payload = _json2.dumps({
                            'description': f'【审核驳回修改】{feedback}',
                            'rework_reason': str(feedback),
                            'original_task_id': task.get('task_id', ''),
                            'retry_count': retry_count + 1,
                        }, ensure_ascii=False)
                        
                        _conn = _pymysql.connect(
                            host='127.0.0.1', port=3306,
                            user='xiaochuan', password='xiaochuan_2026_mjj',
                            database='mojiajun', charset='utf8mb4'
                        )
                        _cur = _conn.cursor()
                        _cur.execute(
                            'INSERT INTO task_queue '
                            '(task_id, parent_sub_task_id, target_agent, task_type, payload, priority, status) '
                            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (rework_task_id, task.get('task_id'), 'molan',
                             'xiaohongshu_note', rework_payload, 2, 'pending')
                        )
                        _conn.commit()
                        _cur.close()
                        _conn.close()
                        logger.info(
                            '🔄 驳回回退：%s 审核不通过 → 生成重写任务 %s (第%d次重试)',
                            task.get('task_id', '?'), rework_task_id, retry_count + 1
                        )
        except Exception:
            pass
        # ============================================
