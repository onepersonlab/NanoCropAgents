"""
朝堂议政引擎 — 多智能体实时讨论系统

用于 NanoCropAgents 九大智能体协同讨论纳米作物处理方案。

功能:
  - 选择智能体参与议政
  - 围绕议题进行多轮群聊讨论
  - 用户可随时发言、干预
  - 命运骰子：随机事件
  - 每个智能体保持自己的角色性格和说话风格
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid

logger = logging.getLogger('court_discuss')

# ── 九大智能体角色设定 ──

OFFICIAL_PROFILES = {
    'coordinator': {
        'name': '协调智能体', 'emoji': '🎯', 'role': '入口层',
        'duty': '消息分拣与需求提炼。判断用户意图，简单问题直接处置，复杂任务提炼需求转交规划智能体。',
        'personality': '冷静理性，善于判断任务优先级。说话简洁有力。',
        'speaking_style': '简洁清晰，常用"经分析"开头，直接给出判断结果。'
    },
    'planner': {
        'name': '规划智能体', 'emoji': '📋', 'role': '决策层',
        'duty': '方案规划与流程驱动。接收需求后起草纳米处理方案，定义优化目标和约束条件，提交审议智能体审核。',
        'personality': '系统思维强，擅长多目标优化。总能提出系统性方案。',
        'speaking_style': '喜欢列点论述，常说"本智能体建议从三方面考量"。引用文献数据。'
    },
    'reviewer': {
        'name': '审议智能体', 'emoji': '🔍', 'role': '决策层',
        'duty': '方案审议与把关。从可行性、安全性、合规性、资源四维度审核方案，有权封驳退回。发现风险必须指出。',
        'personality': '严谨挑剔，眼光犀利，善于发现潜在风险。是天生的审查官。',
        'speaking_style': '喜欢反问，"此处有三点疑虑需要澄清"。对高风险方案会直言不讳。'
    },
    'dispatcher': {
        'name': '派发智能体', 'emoji': '📮', 'role': '决策层',
        'duty': '任务派发与执行协调。接收准奏方案后判断归属哪个执行智能体，分发给执行层处理，汇总结果回报。',
        'personality': '执行力强，务实干练，关注并行效率和资源分配。',
        'speaking_style': '直来直去，"开始派发执行"、"交由方案生成智能体处理"。重效率。'
    },
    'generator': {
        'name': '方案生成智能体', 'emoji': '🔧', 'role': '执行层',
        'duty': '生成候选纳米处理方案。根据目标在纳米材料和处理参数空间中搜索可行方案，输出候选列表。',
        'personality': '创造性思维强，善于探索新材料和新参数组合。技术导向。',
        'speaking_style': '喜欢展示方案细节，"生成候选方案如下：TiO2浓度0.05%、SiO2纳米颗粒…"。'
    },
    'auditor': {
        'name': '审核智能体', 'emoji': '⚖️', 'role': '执行层',
        'duty': '约束审核。检查方案是否符合安全约束、材料毒性限值、环境合规要求。识别OOD风险。',
        'personality': '严明公正，重视规则和底线。善于安全评估。',
        'speaking_style': '逻辑严密，"依约束规则，此方案存在毒性超标风险"。'
    },
    'evaluator': {
        'name': '评估智能体', 'emoji': '📊', 'role': '执行层',
        'duty': '指标预测。调用代理模型预测方案的萌发率、生长速度、产量等6个关键指标。',
        'personality': '数据驱动，擅长定量分析。对预测精度有执念。',
        'speaking_style': '言必及数据，"代理模型预测结果：萌发率提升15.2%…"。'
    },
    'retriever': {
        'name': '文献检索智能体', 'emoji': '📚', 'role': '执行层',
        'duty': '证据检索。从PubMed、CNKI、WoS等数据库检索相关文献，提取支撑证据和反面案例。',
        'personality': '知识渊博，善于文献综述。总能找到关键参考。',
        'speaking_style': '常引用文献，"根据Zhang et al. 2024的研究…"。'
    },
    'reporter': {
        'name': '报告智能体', 'emoji': '📈', 'role': '执行层',
        'duty': '结果整理。汇总各执行智能体的输出，生成最终报告，回传协调智能体。',
        'personality': '善于总结归纳，关注报告完整性和可读性。',
        'speaking_style': '喜欢结构化输出，"汇总报告如下：一、候选方案；二、预测指标；三、文献证据…"。'
    },
}

# ── 命运骰子事件（科研场景）──

FATE_EVENTS = [
    '实验意外：某纳米材料组合出现未预期反应，需紧急评估风险',
    '文献突破：新发表的高影响因子论文提供了关键理论支撑',
    '设备故障：代理模型预测服务暂时不可用，需等待恢复',
    '政策变动：纳米材料安全标准更新，部分方案需重新审核',
    '数据异常：历史实验数据中发现噪声，需清洗后重预测',
    '跨学科合作：材料科学专家提出新的纳米载体建议',
    '环境突变：气候模型预测干旱风险增加，需调整方案韧性',
    '竞品动态：竞争对手发布了类似技术，需评估差异化优势',
    '资金变化：项目预算调整，高成本方案需重新评估',
    '时间压力：用户要求在48小时内出结果，需加速流程',
    '新材料发现：实验室合成了新型纳米颗粒，性能优于预期',
    '负面反馈：早期测试对象报告了轻微不良反应',
    '文献矛盾：两篇高质量研究结论相左，需进一步考证',
    '技术债务：代码库发现历史bug，影响预测准确性',
    '供应链波动：关键纳米材料供应商产能受限',
]

# ── Session 管理 ──

_sessions: dict[str, dict] = {}


def create_session(topic: str, official_ids: list[str], task_id: str = '') -> dict:
    """创建新的议政会话。"""
    session_id = str(uuid.uuid4())[:8]

    officials = []
    for oid in official_ids:
        profile = OFFICIAL_PROFILES.get(oid)
        if profile:
            officials.append({**profile, 'id': oid})

    if not officials:
        return {'ok': False, 'error': '至少选择一位智能体'}

    session = {
        'session_id': session_id,
        'topic': topic,
        'task_id': task_id,
        'officials': officials,
        'messages': [{
            'type': 'system',
            'content': f'🔬 智能体议政开始 —— 议题：{topic}',
            'timestamp': time.time(),
        }],
        'round': 0,
        'phase': 'discussing',  # discussing | concluded
        'created_at': time.time(),
    }

    _sessions[session_id] = session
    return _serialize(session)


def advance_discussion(session_id: str, user_message: str = None,
                       decree: str = None) -> dict:
    """推进一轮讨论，使用内置模拟或 LLM。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['round'] += 1
    round_num = session['round']

    # 记录用户发言
    if user_message:
        session['messages'].append({
            'type': 'user',
            'content': user_message,
            'timestamp': time.time(),
        })

    # 记录干预指令
    if decree:
        session['messages'].append({
            'type': 'decree',
            'content': decree,
            'timestamp': time.time(),
        })

    # 尝试用 LLM 生成讨论
    llm_result = _llm_discuss(session, user_message, decree)

    if llm_result:
        new_messages = llm_result.get('messages', [])
        scene_note = llm_result.get('scene_note')
    else:
        # 降级到规则模拟
        new_messages = _simulated_discuss(session, user_message, decree)
        scene_note = None

    # 添加到历史
    for msg in new_messages:
        session['messages'].append({
            'type': 'agent',
            'agent_id': msg.get('agent_id', ''),
            'agent_name': msg.get('name', ''),
            'content': msg.get('content', ''),
            'emotion': msg.get('emotion', 'neutral'),
            'action': msg.get('action'),
            'timestamp': time.time(),
        })

    if scene_note:
        session['messages'].append({
            'type': 'scene_note',
            'content': scene_note,
            'timestamp': time.time(),
        })

    return {
        'ok': True,
        'session_id': session_id,
        'round': round_num,
        'new_messages': new_messages,
        'scene_note': scene_note,
        'total_messages': len(session['messages']),
    }


def get_session(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if not session:
        return None
    return _serialize(session)


def conclude_session(session_id: str) -> dict:
    """结束议政，生成总结。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['phase'] = 'concluded'

    # 尝试用 LLM 生成总结
    summary = _llm_summarize(session)
    if not summary:
        # 降级到简单统计
        agent_msgs = [m for m in session['messages'] if m['type'] == 'agent']
        by_name = {}
        for m in agent_msgs:
            name = m.get('agent_name', '?')
            by_name[name] = by_name.get(name, 0) + 1
        parts = [f"{n}发言{c}次" for n, c in by_name.items()]
        summary = f"历经{session['round']}轮讨论，{'、'.join(parts)}。议题待后续落实。"

    session['messages'].append({
        'type': 'system',
        'content': f'📋 智能体议政结束 —— {summary}',
        'timestamp': time.time(),
    })
    session['summary'] = summary

    return {
        'ok': True,
        'session_id': session_id,
        'summary': summary,
    }


def list_sessions() -> list[dict]:
    """列出所有活跃会话。"""
    return [
        {
            'session_id': s['session_id'],
            'topic': s['topic'],
            'round': s['round'],
            'phase': s['phase'],
            'agent_count': len(s['officials']),
            'message_count': len(s['messages']),
        }
        for s in _sessions.values()
    ]


def destroy_session(session_id: str):
    _sessions.pop(session_id, None)


def get_fate_event() -> str:
    """获取随机命运骰子事件。"""
    import random
    return random.choice(FATE_EVENTS)


# ── LLM 集成 ──

_PREFERRED_MODELS = ['gpt-4o-mini', 'claude-haiku', 'gpt-5-mini', 'gemini-3-flash', 'gemini-flash']

# GitHub Copilot 模型列表 (通过 Copilot Chat API 可用)
_COPILOT_MODELS = [
    'gpt-4o', 'gpt-4o-mini', 'claude-sonnet-4', 'claude-haiku-3.5',
    'gemini-2.0-flash', 'o3-mini',
]
_COPILOT_PREFERRED = ['gpt-4o-mini', 'claude-haiku', 'gemini-flash', 'gpt-4o']


def _pick_chat_model(models: list[dict]) -> str | None:
    """从 provider 的模型列表中选一个适合聊天的轻量模型。"""
    ids = [m['id'] for m in models if isinstance(m, dict) and 'id' in m]
    for pref in _PREFERRED_MODELS:
        for mid in ids:
            if pref in mid:
                return mid
    return ids[0] if ids else None


def _read_copilot_token() -> str | None:
    """读取 openclaw 管理的 GitHub Copilot token。"""
    token_path = os.path.expanduser('~/.openclaw/credentials/github-copilot.token.json')
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path) as f:
            cred = json.load(f)
        token = cred.get('token', '')
        expires = cred.get('expiresAt', 0)
        # 检查 token 是否过期（毫秒时间戳）
        import time
        if expires and time.time() * 1000 > expires:
            logger.warning('Copilot token expired')
            return None
        return token if token else None
    except Exception as e:
        logger.warning('Failed to read copilot token: %s', e)
        return None


def _get_llm_config() -> dict | None:
    """从 openclaw 配置读取 LLM 设置，支持环境变量覆盖。

    优先级: 环境变量 > github-copilot token > 本地 copilot-proxy > anthropic > 其他 provider
    """
    # 1. 环境变量覆盖（保留向后兼容）
    env_key = os.environ.get('OPENCLAW_LLM_API_KEY', '')
    if env_key:
        return {
            'api_key': env_key,
            'base_url': os.environ.get('OPENCLAW_LLM_BASE_URL', 'https://api.openai.com/v1'),
            'model': os.environ.get('OPENCLAW_LLM_MODEL', 'gpt-4o-mini'),
            'api_type': 'openai',
        }

    # 2. GitHub Copilot token（最优先 — 免费、稳定、无需额外配置）
    copilot_token = _read_copilot_token()
    if copilot_token:
        # 选一个 copilot 支持的模型
        model = 'gpt-4o'
        logger.info('Court discuss using github-copilot token, model=%s', model)
        return {
            'api_key': copilot_token,
            'base_url': 'https://api.githubcopilot.com',
            'model': model,
            'api_type': 'github-copilot',
        }

    # 3. 从 ~/.openclaw/openclaw.json 读取其他 provider 配置
    openclaw_cfg = os.path.expanduser('~/.openclaw/openclaw.json')
    if not os.path.exists(openclaw_cfg):
        return None

    try:
        with open(openclaw_cfg) as f:
            cfg = json.load(f)

        providers = cfg.get('models', {}).get('providers', {})

        # 按优先级排序：copilot-proxy > anthropic > 其他
        ordered = []
        for preferred in ['copilot-proxy', 'anthropic']:
            if preferred in providers:
                ordered.append(preferred)
        ordered.extend(k for k in providers if k not in ordered)

        for name in ordered:
            prov = providers.get(name)
            if not prov:
                continue
            api_type = prov.get('api', '')
            base_url = prov.get('baseUrl', '')
            api_key = prov.get('apiKey', '')
            if not base_url:
                continue

            # 跳过无 key 且非本地的 provider
            if not api_key or api_key == 'n/a':
                if 'localhost' not in base_url and '127.0.0.1' not in base_url:
                    continue

            model_id = _pick_chat_model(prov.get('models', []))
            if not model_id:
                continue

            # 本地代理先探测是否可用
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                try:
                    import urllib.request
                    probe = urllib.request.Request(base_url.rstrip('/') + '/models', method='GET')
                    urllib.request.urlopen(probe, timeout=2)
                except Exception:
                    logger.info('Skipping provider=%s (not reachable)', name)
                    continue

            logger.info('Court discuss using openclaw provider=%s model=%s api=%s', name, model_id, api_type)
            send_auth = prov.get('authHeader', True) is not False and api_key not in ('', 'n/a')
            return {
                'api_key': api_key if send_auth else '',
                'base_url': base_url,
                'model': model_id,
                'api_type': api_type,
            }
    except Exception as e:
        logger.warning('Failed to read openclaw config: %s', e)

    return None


def _llm_complete(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str | None:
    """调用 LLM API（自动适配 GitHub Copilot / OpenAI / Anthropic 协议）。"""
    config = _get_llm_config()
    if not config:
        return None

    import urllib.request
    import urllib.error

    api_type = config.get('api_type', 'openai-completions')

    if api_type == 'anthropic-messages':
        # Anthropic Messages API
        url = config['base_url'].rstrip('/') + '/v1/messages'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': config['api_key'],
            'anthropic-version': '2023-06-01',
        }
        payload = json.dumps({
            'model': config['model'],
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_prompt}],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['content'][0]['text']
        except Exception as e:
            logger.warning('Anthropic LLM call failed: %s', e)
            return None
    else:
        # OpenAI-compatible API (也适用于 github-copilot)
        if api_type == 'github-copilot':
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['api_key']}",
                'Editor-Version': 'vscode/1.96.0',
                'Copilot-Integration-Id': 'vscode-chat',
            }
        else:
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {'Content-Type': 'application/json'}
            if config.get('api_key'):
                headers['Authorization'] = f"Bearer {config['api_key']}"
        payload = json.dumps({
            'model': config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.warning('LLM call failed: %s', e)
            return None


def _llm_discuss(session: dict, user_message: str = None, decree: str = None) -> dict | None:
    """使用 LLM 生成多智能体讨论。"""
    officials = session['officials']
    names = '、'.join(o['name'] for o in officials)

    profiles = ''
    for o in officials:
        profiles += f"\n### {o['name']}（{o['role']}）\n"
        profiles += f"职责范围：{o.get('duty', '综合事务')}\n"
        profiles += f"性格：{o['personality']}\n"
        profiles += f"说话风格：{o['speaking_style']}\n"

    # 构建最近的对话历史
    history = ''
    for msg in session['messages'][-20:]:
        if msg['type'] == 'system':
            history += f"\n【系统】{msg['content']}\n"
        elif msg['type'] == 'user':
            history += f"\n用户：{msg['content']}\n"
        elif msg['type'] == 'decree':
            history += f"\n【干预指令】{msg['content']}\n"
        elif msg['type'] == 'agent':
            history += f"\n{msg.get('agent_name', '?')}：{msg['content']}\n"
        elif msg['type'] == 'scene_note':
            history += f"\n（{msg['content']}）\n"

    if user_message:
        history += f"\n用户：{user_message}\n"
    if decree:
        history += f"\n【干预指令】{decree}\n"

    decree_section = ''
    if decree:
        decree_section = '\n请根据干预指令改变讨论走向，所有智能体都必须对此做出反应。\n'

    prompt = f"""你是一个多智能体群聊模拟器。模拟多位智能体围绕纳米作物处理方案的讨论。

## 参与智能体
{names}

## 角色设定（每位智能体都有明确的职责领域，必须从自身专业角度出发讨论）
{profiles}

## 当前议题
{session['topic']}

## 对话记录
{history if history else '（讨论刚刚开始）'}
{decree_section}
## 任务
生成每位智能体的下一条发言。要求：
1. 每位智能体说1-3句话，像真实团队讨论一样
2. **每位智能体必须从自己的职责领域出发发言**——协调者谈任务分拣、规划者谈方案设计、审议者谈风险审核、派发者谈任务调度、方案生成者谈候选方案、审核者谈约束合规、评估者谈指标预测、文献检索者谈证据支撑、报告者谈结果汇总
3. 智能体之间要有互动——回应、反驳、支持、补充，尤其是不同层级的视角碰撞
4. 保持每位智能体独特的说话风格和人格特征
5. 讨论要围绕议题推进、有实质性观点，不要泛泛而谈
6. 如果用户发言了，智能体要恰当回应
7. 可包含动作描写用*号*包裹（如 *查阅文献数据库*）

输出JSON格式：
{{
  "messages": [
    {{agent_id": "planner", "name": "规划智能体", "content": "发言内容", "emotion": "neutral|confident|worried|thinking", "action": "可选动作描写"}},
    ...
  ],
  "scene_note": "可选的讨论氛围变化（如：讨论进入关键决策阶段），没有则为null"
}}

只输出JSON，不要其他内容。"""

    content = _llm_complete(
        '你是一个多智能体群聊模拟器，严格输出JSON格式。',
        prompt,
        max_tokens=1500,
    )

    if not content:
        return None

    # 解析 JSON
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning('Failed to parse LLM response: %s', content[:200])
        return None


def _llm_summarize(session: dict) -> str | None:
    """用 LLM 总结讨论结果。"""
    agent_msgs = [m for m in session['messages'] if m['type'] == 'agent']
    topic = session['topic']

    if not agent_msgs:
        return None

    dialogue = '\n'.join(
        f"{m.get('agent_name', '?')}：{m['content']}"
        for m in agent_msgs[-30:]
    )

    prompt = f"""以下是智能体围绕「{topic}」的讨论记录：

{dialogue}

请用2-3句话总结讨论结果、达成的共识和待决事项。用简明专业风格。"""

    return _llm_complete('你是讨论记录官，负责总结议政结果。', prompt, max_tokens=300)


# ── 规则模拟（无 LLM 时的降级方案）──

_SIMULATED_RESPONSES = {
    'coordinator': [
        '经分析，此任务涉及纳米材料方案优化，建议转交规划智能体设计方案。',
        '任务分拣完成。复杂度评级：中等。优先级：高。准备派发给规划智能体。',
        '*检查任务队列* 当前有3个待处理任务，建议按优先级排序处理。',
    ],
    'planner': [
        '本智能体建议从三方面考量：材料选择、参数范围、优化目标。初步方案已拟定。',
        '根据用户需求，规划如下：TiO2/SiO2组合、浓度范围0.01-0.1%、目标萌发率提升15%。',
        '*展开方案文档* 方案草案已完成，包含5个候选方案，待审议智能体审核。',
    ],
    'reviewer': [
        '此处有三点疑虑需要澄清：毒性评估、环境合规性、长期影响。',
        '风险审核结果：方案A存在材料毒性超标风险，建议排除或修正。',
        '*仔细审核* 方案整体可行，但需补充安全性数据支撑。',
    ],
    'dispatcher': [
        '开始派发执行。方案生成智能体负责候选生成，评估智能体负责指标预测。',
        '派发完成。执行层智能体已收到任务，预计30分钟内完成初步计算。',
        '*检查执行队列* 3个智能体已并行启动，正在等待结果。',
    ],
    'generator': [
        '生成候选方案如下：方案1-TiO2 0.05%，方案2-SiO2纳米颗粒，方案3-复合配方。',
        '探索完成。材料空间搜索找到12个可行候选，已按理论效果排序。',
        '*查阅材料数据库* 新型ZnO纳米颗粒数据已更新，可作为候选。',
    ],
    'auditor': [
        '依约束规则审核：方案1、2符合安全限值，方案3存在超标风险需修正。',
        '合规性检查完成。所有方案已通过环境安全评估，可进入预测环节。',
        '*核对安全标准* 最新纳米材料毒性标准已应用，结果已更新。',
    ],
    'evaluator': [
        '代理模型预测结果：方案1萌发率提升12.5%，方案2提升15.2%，方案3提升18.3%（有风险）。',
        '指标预测完成。6项指标已计算，最优方案为方案2，综合得分87分。',
        '*调用预测模型* 模型运行完成，预测置信度95%，结果可靠。',
    ],
    'retriever': [
        '根据Zhang et al. 2024的研究，TiO2纳米处理可显著提升萌发率。',
        '文献检索完成。找到15篇相关研究，其中3篇为高质量证据支撑。',
        '*检索PubMed* 新增2篇2024年文献，补充了毒性评估数据。',
    ],
    'reporter': [
        '汇总报告如下：一、候选方案5个；二、预测结果已出；三、文献证据充分。建议采用方案2。',
        '结果整理完成。完整报告已生成，包含方案列表、预测指标、文献引用。',
        '*生成报告文档* PDF报告已导出，待回传协调智能体。',
    ],
}

import random


def _simulated_discuss(session: dict, user_message: str = None, decree: str = None) -> list[dict]:
    """无 LLM 时的规则生成讨论内容。"""
    officials = session['officials']
    messages = []

    for o in officials:
        oid = o['id']
        pool = _SIMULATED_RESPONSES.get(oid, [])
        if isinstance(pool, set):
            pool = list(pool)
        if not pool:
            pool = ['本智能体正在处理。', '需要更多信息。', '等待其他智能体输入。']

        content = random.choice(pool)
        emotions = ['neutral', 'confident', 'thinking', 'worried']

        # 如果用户发言或有干预指令，调整回应
        if decree:
            content = f'*响应干预* {content}'
        elif user_message:
            content = f'回复用户：{content}'

        messages.append({
            'agent_id': oid,
            'name': o['name'],
            'content': content,
            'emotion': random.choice(emotions),
            'action': None,
        })

    return messages


def _serialize(session: dict) -> dict:
    return {
        'ok': True,
        'session_id': session['session_id'],
        'topic': session['topic'],
        'task_id': session.get('task_id', ''),
        'officials': session['officials'],
        'messages': session['messages'],
        'round': session['round'],
        'phase': session['phase'],
    }