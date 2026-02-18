#!/usr/bin/env python3
"""
Illustration Prompt Processor V2 — Обновлённая версия
Новая логика:
1. Строит "библию" сущностей (персонажи, объекты, локации)
2. Генерирует сценарий из 4–8 смысловых сцен (вместо механического деления)
3. Для каждой сцены создаёт промпт, используя библию и контекст

Цель: согласованность иллюстраций с текстом и между собой.
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from dotenv import load_dotenv

DEFAULT_NEGATIVE = (
    "text, watermark, logo, low quality, blurry, distorted, extra limbs, deformed, cropped, frame"
)


class IllustrationPromptProcessorV2:
    def __init__(self, config_file: Optional[str] = None):
        self._load_config(config_file)
        if not self.api_key:
            raise ValueError("API ключ OpenRouter не найден в конфигурации")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/illustration-prompt-processor",
            "X-Title": "Illustration Prompt Processor V2",
        }
        self.stats = {
            "api_calls": 0,
            "total_tokens_used": 0,
            "processing_time": 0.0,
        }
        self.inline_entities = True  # будет установлено в run()
        self.model = os.getenv("DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")

    def _load_config(self, config_file: Optional[str]):
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)
        else:
            for env_name in [".env", "config.env", "settings.env"]:
                if Path(env_name).exists():
                    load_dotenv(env_name)
                    break
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "1400"))
        self.budget_model = os.getenv("BUDGET_MODEL", "meta-llama/llama-3.1-8b-instruct")
        self.quality_model = os.getenv("QUALITY_MODEL", "openai/gpt-4o")

    # -------------------------- LLM Core --------------------------

    def _call_llm(self, prompt: str, *, system: Optional[str] = None, retry_count: int = 3,
                  max_tokens: Optional[int] = None) -> Optional[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [],
            "temperature": self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": prompt})

        for attempt in range(retry_count):
            try:
                self.stats["api_calls"] += 1
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    if "usage" in data:
                        self.stats["total_tokens_used"] += data["usage"].get("total_tokens", 0)
                    return content
                elif resp.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                else:
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"⚠️ Ошибка LLM вызова (попытка {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        return None

    # -------------------------- Bible --------------------------

    @staticmethod
    def _new_bible_template() -> Dict[str, Any]:
        return {
            "metadata": {},
            "style_guide": {},
            "characters": [],
            "objects": [],
            "locations": [],
            "state": {"inventory": {}, "relationships": {}, "timeline": []},
        }

    def _extract_entities(self, full_text: str, style_hint: Optional[str]) -> Dict[str, Any]:
        system = (
            "You extract structured entities from narratives. Output STRICT JSON with keys:"
            " characters, objects, locations. Characters: id, canonical_name, aliases (array),"
            " role, appearance, colors (array, optional), traits (array, optional),"
            " iconic_items (array, optional), do_not_change (array, important)."
            " Objects: id, name, appearance, symbols (array, optional), do_not_change (array)."
            " Locations: id, name, description, atmosphere (optional)."
            " Use only facts explicitly present in the text. No inventions."
        )
        style_line = f"\nStyle hint: {style_hint}" if style_hint else ""
        prompt = (
            "Extract entities from the TEXT below. JSON only, no comments.\n"
            f"{style_line}\n"
            "TEXT:\n"
            f'"""{full_text}"""\n'
        )
        content = self._call_llm(prompt, system=system, max_tokens=min(self.max_tokens, 1200))
        if not content:
            return {"characters": [], "objects": [], "locations": []}
        try:
            data = json.loads(content)
            data.setdefault("characters", [])
            data.setdefault("objects", [])
            data.setdefault("locations", [])
            return data
        except Exception as e:
            print(f"❌ Ошибка парсинга entities: {e}")
            return {"characters": [], "objects": [], "locations": []}

    @staticmethod
    def _index_by_id(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {item.get("id") or item.get("canonical_name") or item.get("name"): item for item in items if item}

    @staticmethod
    def _merge_item(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(old)
        for key, value in new.items():
            if value is None:
                continue
            if isinstance(value, list):
                seen = set(merged.get(key, []) or [])
                for v in value:
                    if v not in seen:
                        (merged.setdefault(key, [])).append(v)
                        seen.add(v)
            elif isinstance(value, dict):
                merged[key] = {**merged.get(key, {}), **value}
            else:
                if not merged.get(key):
                    merged[key] = value
        return merged

    def _merge_bible(self, base: Dict[str, Any], additions: Dict[str, Any]) -> Dict[str, Any]:
        if not base:
            base = self._new_bible_template()
        for section in ["characters", "objects", "locations"]:
            base_section = self._index_by_id(base.get(section, []))
            add_section = self._index_by_id(additions.get(section, []))
            for item_id, new_item in add_section.items():
                if item_id in base_section:
                    base_section[item_id] = self._merge_item(base_section[item_id], new_item)
                else:
                    base_section[item_id] = new_item
            base[section] = list(base_section.values())
        base.setdefault("state", {"inventory": {}, "relationships": {}, "timeline": []})
        return base

    # -------------------------- Script Generation --------------------------

    def _generate_script(self, full_text: str, bible: Dict[str, Any], style_hint: Optional[str], setting_hint: str, target_scenes: int = 8, max_retries: int = 5) -> List[Dict[str, Any]]:
        """
        Генерирует сценарий из заданного количества визуально выразительных сцен.
        Каждая сцена содержит: title, summary, entities (id), timing.
        """
        characters = bible.get("characters", [])
        locations = bible.get("locations", [])
        objects = bible.get("objects", [])

        char_names = [c.get("canonical_name") or c.get("name") for c in characters if c.get("canonical_name") or c.get("name")]
        loc_names = [l.get("name") for l in locations if l.get("name")]

        # Адаптируем инструкции в зависимости от количества сцен
        if target_scenes <= 8:
            scene_range = f"{target_scenes} key scenes"
            timing_options = "'beginning', 'middle', 'climax', 'end'"
        else:
            scene_range = f"{target_scenes} scenes that cover the entire story"
            timing_options = "'beginning', 'early', 'middle', 'late', 'climax', 'end'"

        system = (
            "You are a narrative scriptwriter for illustrated stories. "
            f"Analyze the full text and break it into {scene_range} that capture the story arc. "
            "Each scene must be self-contained and visually illustratable. "
            "Output STRICT JSON: array of objects with keys: "
            "title (string), summary (1-2 sentences), entities (array of entity IDs from the provided bible), timing (string: {timing_options}). "
            "Only use entity IDs that are in the bible. Do not invent new entities. "
            "For longer stories, create more detailed scene breakdowns."
        )

        prompt = (
            f"Style: {style_hint or 'realistic'}\n"
            f"Setting context: {setting_hint or 'general'}\n"
            f"Known characters: {', '.join(char_names) or 'None'}\n"
            f"Known locations: {', '.join(loc_names) or 'None'}\n\n"
            f"FULL TEXT:\n"
            f'"""{full_text}"""\n\n'
            f"BIBLE (for entity IDs):\n"
            f"{json.dumps({k: v for k, v in bible.items() if k in ['characters', 'objects', 'locations']}, ensure_ascii=False, indent=2)}\n\n"
            "Now generate the script as JSON array."
        )

        print(f"🎬 Генерация сценария из сцен...")
        
        # Retry логика для генерации сценария
        for attempt in range(max_retries):
            print(f"   🔄 Попытка {attempt + 1}/{max_retries}...")
            
            content = self._call_llm(prompt, system=system, max_tokens=36000)
            if not content:
                print(f"   ⚠️ LLM не вернул контент")
                if attempt < max_retries - 1:
                    delay = 2 + (2 ** attempt)
                    print(f"   ⏳ Ожидание {delay} секунд...")
                    time.sleep(delay)
                    continue
                else:
                    break

            print(f"   🔍 LLM вернул контент длиной {len(content)} символов")
            print(f"   📝 Первые 200 символов: {content[:200]}...")
            
            # Попытка парсинга JSON
            try:
                script = json.loads(content)
                if not isinstance(script, list):
                    raise ValueError("Script is not a list")
                print(f"   ✅ Сценарий успешно распарсен: {len(script)} сцен (попытка {attempt + 1})")
                return script
            except Exception as e:
                print(f"   ❌ Ошибка парсинга сценария: {e}")
                print(f"   🔍 Поиск JSON в контенте...")
                
                # Попробуем найти JSON в тексте
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        json_content = json_match.group(0)
                        script = json.loads(json_content)
                        if isinstance(script, list):
                            print(f"   ✅ JSON найден и распарсен: {len(script)} сцен (попытка {attempt + 1})")
                            return script
                    except:
                        pass
                
                # Если это не последняя попытка, ждем и пробуем снова
                if attempt < max_retries - 1:
                    delay = 2 + (2 ** attempt)
                    print(f"   ⏳ Ожидание {delay} секунд...")
                    time.sleep(delay)
                    continue
        
        # Если все попытки исчерпаны
        print(f"   ⚠️ Все попытки исчерпаны. Не удалось сгенерировать сценарий")
        return []

    # -------------------------- Utility --------------------------

    @staticmethod
    def _normalize_style_guide(bible: Dict[str, Any], style: Optional[str]) -> None:
        style_guide = bible.setdefault("style_guide", {})
        if style:
            style_guide["visual_style"] = style
        style_guide.setdefault("illustration_rules", [
            "Avoid logos, text, and watermarks",
            "Keep historical consistency of clothing and artifacts"
        ])

    @staticmethod
    def _compose_setting_hint(style_guide: Dict[str, Any], *, era: Optional[str] = None,
                              region: Optional[str] = None, genre: Optional[str] = None,
                              setting: Optional[str] = None) -> str:
        parts: List[str] = []
        if setting:
            parts.append(setting)
        if era:
            parts.append(era)
        if region:
            parts.append(region)
        if genre:
            parts.append(genre)
        if style_guide.get("visual_style"):
            parts.append(f"style {style_guide['visual_style']}")
        return ", ".join([p for p in parts if p])

    @staticmethod
    def _extract_aliases(entity: Dict[str, Any]) -> List[str]:
        aliases: List[str] = []
        for key in ["canonical_name", "name"]:
            if entity.get(key):
                aliases.append(str(entity[key]))
        for a in entity.get("aliases", []) or []:
            if a:
                aliases.append(str(a))
        uniq: List[str] = []
        seen: set = set()
        for x in aliases:
            low = x.lower()
            if low not in seen:
                uniq.append(x)
                seen.add(low)
        return uniq

    def _detect_present_entities(self, scene_summary: str, bible: Dict[str, Any]) -> List[str]:
        present: List[str] = []
        text_low = scene_summary.lower()
        for section in ["characters", "objects", "locations"]:
            for ent in bible.get(section, []) or []:
                ent_id = ent.get("id") or ent.get("canonical_name") or ent.get("name")
                if not ent_id:
                    continue
                aliases = self._extract_aliases(ent)
                if any(a.lower() in text_low for a in aliases):
                    present.append(str(ent_id))
        seen: set = set()
        return [eid for eid in present if not (eid in seen or seen.add(eid))]

    @staticmethod
    def _cards_for_entities(bible: Dict[str, Any], entity_ids: List[str]) -> List[Dict[str, Any]]:
        def pick_fields(ent: Dict[str, Any]) -> Dict[str, Any]:
            keys = [
                "id", "canonical_name", "name", "role", "appearance",
                "colors", "traits", "iconic_items", "do_not_change",
                "description", "atmosphere", "visual_profile",
            ]
            return {k: ent[k] for k in keys if k in ent and ent[k]}

        ent_index: Dict[str, Dict[str, Any]] = {}
        for section in ["characters", "objects", "locations"]:
            for ent in bible.get(section, []) or []:
                ent_id = ent.get("id") or ent.get("canonical_name") or ent.get("name")
                if ent_id:
                    ent_index[str(ent_id)] = ent

        return [pick_fields(ent_index[eid]) for eid in entity_ids if eid in ent_index]

    @staticmethod
    def _summarize_card_en(card: Dict[str, Any]) -> str:
        name = card.get("canonical_name") or card.get("name") or card.get("id") or "entity"
        role = card.get("role")
        appearance = card.get("appearance")
        colors = ", ".join(card.get("colors", []) or [])
        traits = ", ".join(card.get("traits", []) or [])
        iconic = ", ".join(card.get("iconic_items", []) or [])
        must_keep = ", ".join(card.get("do_not_change", []) or [])

        vp = card.get("visual_profile") or {}
        age = vp.get("age")
        gender = vp.get("gender")
        face = vp.get("face_features") or vp.get("face")
        hairstyle = vp.get("hairstyle")
        facial_hair = vp.get("facial_hair")
        clothing = vp.get("clothing")
        headwear = vp.get("headwear")
        footwear = vp.get("footwear")
        accessories = vp.get("accessories")
        signature_colors = ", ".join(vp.get("signature_colors", []) or [])

        # Создаем более естественное описание для интеграции в промпт
        parts: List[str] = []
        
        # Основные характеристики
        if age and gender:
            parts.append(f"a {age} {gender}")
        elif age:
            parts.append(f"a {age} person")
        elif gender:
            parts.append(f"a {gender}")
        
        # Внешность
        if face:
            parts.append(f"with {face}")
        if hairstyle:
            parts.append(f"wearing {hairstyle}")
        if facial_hair:
            parts.append(f"with {facial_hair}")
        
        # Одежда
        if clothing:
            parts.append(f"dressed in {clothing}")
        if headwear:
            parts.append(f"wearing {headwear}")
        if footwear:
            parts.append(f"with {footwear}")
        if accessories:
            parts.append(f"carrying {accessories}")
        
        # Цвета
        if signature_colors:
            parts.append(f"in {signature_colors} colors")
        
        # Характерные черты
        if traits:
            parts.append(f"showing {traits}")
        
        # Иконные предметы
        if iconic:
            parts.append(f"holding {iconic}")
        
        # Роль (если не указана в названии)
        if role and role.lower() not in name.lower():
            parts.append(f"acting as {role}")

        desc = " ".join(p for p in parts if p)
        if not desc:
            desc = str(name)
        
        # Добавляем важные детали, которые нельзя менять
        if must_keep:
            desc += f" (keep: {must_keep})"
            
        return desc

    def _enrich_bible_characters(self, bible: Dict[str, Any], setting_hint: str) -> Dict[str, Any]:
        characters = bible.get("characters") or []
        if not characters:
            return bible

        system = (
            "You are a character visual designer. For each input character, return a STRICT JSON object"
            " with fields: id, visual_profile { age (string), gender (string), face_features (string),"
            " hairstyle (string), facial_hair (string, optional), clothing (string), headwear (string, optional),"
            " footwear (string, optional), accessories (string, optional), signature_colors (array of strings) }"
            ". Keep designs coherent with the given setting. If certain details are known (appearance, iconic items),"
            " incorporate and expand them tastefully. If unknown, invent plausible details consistent with the setting."
        )

        enriched_index: Dict[str, Dict[str, Any]] = {}
        for ch in characters:
            ch_id = ch.get("id") or ch.get("canonical_name") or ch.get("name")
            if not ch_id:
                continue
            if isinstance(ch.get("visual_profile"), dict) and ch["visual_profile"].get("age"):
                enriched_index[str(ch_id)] = ch
                continue

            base = {
                "id": ch_id,
                "canonical_name": ch.get("canonical_name"),
                "role": ch.get("role"),
                "appearance": ch.get("appearance"),
                "iconic_items": ch.get("iconic_items", []),
                "traits": ch.get("traits", []),
            }
            setting_line = f"Setting: {setting_hint}" if setting_hint else ""
            prompt = (
                "Enrich the following character with a detailed visual_profile. JSON only.\n"
                f"{setting_line}\n"
                "CHARACTER:\n" + json.dumps(base, ensure_ascii=False)
            )
            content = self._call_llm(prompt, system=system, max_tokens=600)
            if not content:
                enriched_index[str(ch_id)] = ch
                continue
            try:
                data = json.loads(content)
                vp = data.get("visual_profile") if isinstance(data, dict) else None
                if isinstance(vp, dict):
                    ch["visual_profile"] = {**ch.get("visual_profile", {}), **vp}
                enriched_index[str(ch_id)] = ch
            except Exception as e:
                print(f"⚠️ Не удалось обогатить персонажа {ch_id}: {e}")
                enriched_index[str(ch_id)] = ch
        bible["characters"] = list(enriched_index.values())
        return bible

    def _inline_entity_descriptions(self, base_prompt: str, cards: List[Dict[str, Any]],
                                    style_guide: Dict[str, Any], *, max_cards: int = 8,
                                    max_chars: int = 900) -> str:
        if not cards:
            return base_prompt

        def priority(card: Dict[str, Any]) -> int:
            if card.get("role") or ("traits" in card or "iconic_items" in card):
                return 0  # character
            if "appearance" in card:
                return 1  # object
            return 2  # location

        ordered = sorted(cards, key=priority)
        selected: List[str] = []
        total_len = 0
        for card in ordered[:max_cards]:
            line = self._summarize_card_en(card)
            if not line or total_len + len(line) > max_chars:
                continue
            selected.append(line)
            total_len += len(line)

        if not selected:
            return base_prompt

        style_hint = style_guide.get("visual_style")
        style_part = f" Style: {style_hint}." if style_hint else ""
        inline = "Key visual details for consistency: " + "; ".join(selected) + "." + style_part
        return base_prompt.strip() + "\n" + inline

    # -------------------------- Scene Prompt Generation --------------------------

    def _generate_prompt_for_scene(self, scene: Dict[str, Any], full_text: str, bible: Dict[str, Any], max_retries: int = 5) -> Optional[Dict[str, Any]]:
        entities = scene.get("entities", [])
        cards = self._cards_for_entities(bible, entities)

        style_guide = bible.get("style_guide", {})
        style_hint = style_guide.get("visual_style", "")
        rules = style_guide.get("illustration_rules", [])

        style_str = f"Style: {style_hint}." if style_hint else ""
        rules_str = "\n".join(f"- {r}" for r in rules) if rules else ""

        # Создаем детальное описание всех сущностей сцены
        entity_details = []
        for card in cards:
            if self._summarize_card_en(card):
                entity_details.append(self._summarize_card_en(card))

        system = (
            "You are an expert prompt engineer for image generation models (e.g. FLUX). "
            "Create a single, vivid, and cinematic image prompt that INTEGRATES all the visual details "
            "from the character and object descriptions into a cohesive scene description. "
            "DO NOT just list the details - weave them naturally into the scene narrative. "
            "The prompt should read as one flowing description, not a collection of separate details. "
            "Avoid text, watermarks, logos. Be cinematic and emotionally resonant."
        )

        prompt = (
            f"SCENE TITLE: {scene.get('title', 'Untitled')}\n"
            f"SUMMARY: {scene.get('summary', '')}\n\n"
            f"VISUAL ELEMENTS TO INTEGRATE INTO THE SCENE:\n"
            f"{chr(10).join(f'• {detail}' for detail in entity_details)}\n\n"
            f"{style_str}\n"
            f"{rules_str}\n\n"
            "Create a SINGLE, FLOWING prompt that naturally incorporates all these visual elements "
            "into a cohesive scene description. Do not list them separately.\n\n"
            "Output JSON with: prompt (string), negative_prompt (string), title (string)."
        )

        # Retry логика для генерации промптов
        scene_title = scene.get('title', 'Untitled')
        print(f"🖼️ Генерация промпта для сцены: {scene_title}")
        
        for attempt in range(max_retries):
            print(f"   🔄 Попытка {attempt + 1}/{max_retries}...")
            
            content = self._call_llm(prompt, system=system, max_tokens=5000)
            if not content:
                print(f"   ⚠️ LLM не вернул контент")
                if attempt < max_retries - 1:
                    delay = 2 + (2 ** attempt)  # Минимум 2 сек, увеличиваем при неудачах
                    print(f"   ⏳ Ожидание {delay} секунд...")
                    time.sleep(delay)
                    continue
                else:
                    break

            # Попытка парсинга JSON
            try:
                parsed = json.loads(content)
                final_prompt = (parsed.get("prompt") or "").strip()
                if not final_prompt:
                    print(f"   ⚠️ Пустой промпт в ответе")
                    if attempt < max_retries - 1:
                        delay = 2 + (2 ** attempt)
                        print(f"   ⏳ Ожидание {delay} секунд...")
                        time.sleep(delay)
                        continue
                    else:
                        break

                # Успешный парсинг
                print(f"   ✅ Успешно сгенерирован промпт (попытка {attempt + 1})")
                return {
                    "index": None,
                    "title": parsed.get("title") or scene.get("title", "Scene"),
                    "prompt": final_prompt,
                    "negative_prompt": (parsed.get("negative_prompt") or DEFAULT_NEGATIVE).strip(),
                    "summary": scene.get("summary"),
                    "present_entities": entities,
                    "timing": scene.get("timing"),
                    "source_excerpt": scene.get("summary")
                }
            except Exception as e:
                print(f"   ❌ Ошибка парсинга JSON: {e}")
                print(f"   🔍 Поиск JSON в контенте...")
                
                # Попробуем найти JSON в тексте
                import re
                json_match = re.search(r'\{[^}]*"prompt"[^}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        json_content = json_match.group(0)
                        parsed = json.loads(json_content)
                        final_prompt = (parsed.get("prompt") or "").strip()
                        if final_prompt:
                            print(f"   ✅ JSON найден и распарсен (попытка {attempt + 1})")
                            return {
                                "index": None,
                                "title": parsed.get("title") or scene.get("title", "Scene"),
                                "prompt": final_prompt,
                                "negative_prompt": (parsed.get("negative_prompt") or DEFAULT_NEGATIVE).strip(),
                                "summary": scene.get("summary"),
                                "present_entities": entities,
                                "timing": scene.get("timing"),
                                "source_excerpt": scene.get("summary")
                            }
                    except:
                        pass
                
                # Если это не последняя попытка, ждем и пробуем снова
                if attempt < max_retries - 1:
                    delay = 2 + (2 ** attempt)
                    print(f"   ⏳ Ожидание {delay} секунд...")
                    time.sleep(delay)
                    continue
        
        # Если все попытки исчерпаны, создаем простой промпт на основе сцены
        print(f"   ⚠️ Все попытки исчерпаны. Создаем простой промпт")
        simple_prompt = f"Scene: {scene.get('title', 'Untitled')}. {scene.get('summary', '')}"
        
        # Добавляем ключевые детали сущностей для fallback
        if cards:
            entity_summaries = [self._summarize_card_en(card) for card in cards if self._summarize_card_en(card)]
            if entity_summaries:
                simple_prompt += f" Featuring: {', '.join(entity_summaries)}"
        
        return {
            "index": None,
            "title": scene.get("title", "Scene"),
            "prompt": simple_prompt,
            "negative_prompt": DEFAULT_NEGATIVE,
            "summary": scene.get("summary"),
            "present_entities": entities,
            "timing": scene.get("timing"),
            "source_excerpt": scene.get("summary")
        }

    # -------------------------- Public Orchestration --------------------------

    def run(self, input_file: str, output_file: str, *, parts: int = 6, style: Optional[str] = None,
            model_choice: str = "default", bible_in: Optional[str] = None,
            bible_out: Optional[str] = None, book_title: Optional[str] = None,
            book_author: Optional[str] = None, inline_entities: bool = True,
            enrich_characters: bool = True, era: Optional[str] = None,
            region: Optional[str] = None, genre: Optional[str] = None,
            setting: Optional[str] = None, audio_duration: Optional[float] = None,
            seconds_per_illustration: float = 15.0) -> bool:
        start = time.time()
        try:
            # --- Модель ---
            if model_choice == "budget":
                self.model = self.budget_model
            elif model_choice == "quality":
                self.model = self.quality_model
            self.inline_entities = inline_entities

            in_path = Path(input_file)
            if not in_path.exists():
                print(f"❌ Файл не найден: {input_file}")
                return False
            text = in_path.read_text(encoding="utf-8").strip()
            if not text:
                print("❌ Пустой входной текст")
                return False

            # --- Библия ---
            bible: Dict[str, Any]
            if bible_in and Path(bible_in).exists():
                try:
                    bible = json.loads(Path(bible_in).read_text(encoding="utf-8"))
                    print(f"📖 Загружена существующая bible: {bible_in}")
                except Exception as e:
                    print(f"⚠️ Не удалось прочитать bible-in: {e}; будет создана новая")
                    bible = self._new_bible_template()
            else:
                bible = self._new_bible_template()

            extracted = self._extract_entities(text, style)
            bible = self._merge_bible(bible, extracted)
            self._normalize_style_guide(bible, style)

            bible.setdefault("metadata", {})
            bible["metadata"].update({
                "source_file": str(in_path),
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "style": style,
                "book": {"title": book_title, "author": book_author},
            })

            # --- Обогащение персонажей ---
            if enrich_characters:
                setting_hint = self._compose_setting_hint(
                    bible.get("style_guide", {}), era=era, region=region, genre=genre, setting=setting
                )
                bible = self._enrich_bible_characters(bible, setting_hint)

            # --- Сохранение библии ---
            if bible_out:
                out_path_bible = Path(bible_out)
                out_path_bible.parent.mkdir(parents=True, exist_ok=True)
                out_path_bible.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"📖 Bible сохранена: {out_path_bible}")

            # --- Расчет количества сцен на основе аудио ---
            target_parts = parts
            if audio_duration:
                calculated_parts = max(4, int(audio_duration / seconds_per_illustration))
                target_parts = min(calculated_parts, parts)  # Не превышаем запрошенное количество
                print(f"🎵 Длительность аудио: {audio_duration:.1f}с")
                print(f"📊 Целевое количество иллюстраций: {calculated_parts} (по {seconds_per_illustration}с)")
                print(f"🎯 Финальное количество: {target_parts}")

            # --- Генерация сценария ---
            print("🎬 Генерация сценария из сцен...")
            setting_hint = self._compose_setting_hint(
                bible.get("style_guide", {}), era=era, region=region, genre=genre, setting=setting
            )
            script = self._generate_script(text, bible, style, setting_hint, target_parts)
            if not script:
                print("❌ Не удалось сгенерировать сценарий")
                return False
            print(f"✅ Сгенерировано {len(script)} сцен")

            # Ограничение по количеству
            script = script[:target_parts]

            # --- Генерация иллюстраций ---
            illustrations = []
            for i, scene in enumerate(script, start=1):
                print(f"🖼️ Генерация промпта для сцены {i}/{len(script)}: {scene.get('title', 'Без названия')}...")
                illustration = self._generate_prompt_for_scene(scene, text, bible)
                if illustration:
                    illustration["index"] = i
                    illustrations.append(illustration)

            # --- Сохранение результата ---
            result = {
                "metadata": {
                    "source_file": str(in_path),
                    "generated_at": datetime.now().isoformat(),
                    "model": self.model,
                    "style": style,
                    "requested_parts": parts,
                    "created_parts": len(illustrations),
                    "book": {"title": book_title, "author": book_author},
                    "api_calls": self.stats["api_calls"],
                    "tokens_used": self.stats["total_tokens_used"],
                },
                "illustrations": illustrations,
                "bible_ref": str(bible_out) if bible_out else None,
                "script": script  # для отладки
            }

            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

            self.stats["processing_time"] = time.time() - start
            print(f"✅ Описания иллюстраций сохранены: {out_path}")
            print(f"📊 Сцен создано: {len(illustrations)}, API вызовов: {self.stats['api_calls']}, "
                  f"Время: {self.stats['processing_time']:.1f}с")
            return True

        except Exception as e:
            print(f"❌ Ошибка генерации иллюстраций: {e}")
            import traceback
            traceback.print_exc()
            return False


# ======================== CLI ========================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Генерация промптов иллюстраций из текста с поддержкой story bible",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  python illustration_prompt_processor_v2.py input.txt \\\n"
            "      -o illustrations.json --bible-out bible.json --parts 6 --style folk\n"
        ),
    )
    parser.add_argument("input_file", help="Входной текстовый файл")
    parser.add_argument("-o", "--output", required=True, help="Выходной JSON файл с иллюстрациями")
    parser.add_argument("--config", help="Файл конфигурации .env")
    parser.add_argument("--bible-in", help="Путь к существующей bible.json для слияния")
    parser.add_argument("--bible-out", help="Куда сохранить обновлённую bible.json")
    parser.add_argument("--parts", type=int, default=6, help="Максимальное количество сцен")
    parser.add_argument("--style", help="Желаемый визуальный стиль (для style_guide)")
    parser.add_argument(
        "--model",
        choices=["default", "budget", "quality"],
        default="default",
        help="Выбор пресета модели",
    )
    parser.add_argument("--title", help="Название книги (опционально)")
    parser.add_argument("--author", help="Автор книги (опционально)")
    parser.add_argument(
        "--no-inline-entities",
        action="store_true",
        help="Не добавлять развёрнутые описания сущностей в итоговый prompt",
    )
    parser.add_argument(
        "--no-enrich-characters",
        action="store_true",
        help="Не обогащать персонажей подробным визуальным профилем",
    )
    parser.add_argument("--era", help="Эпоха (например '19th century')")
    parser.add_argument("--region", help="Регион (например 'Slavic/Russian village')")
    parser.add_argument("--genre", help="Жанр (например 'folk tale')")
    parser.add_argument("--setting", help="Краткое описание сеттинга")
    parser.add_argument("--audio-duration", type=float, help="Длительность аудио в секундах")
    parser.add_argument("--seconds-per-illustration", type=float, default=15.0, 
                       help="Количество секунд на одну иллюстрацию (по умолчанию 15)")

    args = parser.parse_args()

    try:
        proc = IllustrationPromptProcessorV2(args.config)
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("Создайте файл .env или config.env с вашим API ключом")
        return 1

    ok = proc.run(
        input_file=args.input_file,
        output_file=args.output,
        parts=args.parts,
        style=args.style,
        model_choice=args.model,
        bible_in=args.bible_in,
        bible_out=args.bible_out,
        book_title=args.title,
        book_author=args.author,
        inline_entities=(not args.no_inline_entities),
        enrich_characters=(not args.no_enrich_characters),
        era=args.era,
        region=args.region,
        genre=args.genre,
        setting=args.setting,
        audio_duration=args.audio_duration,
        seconds_per_illustration=args.seconds_per_illustration,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())