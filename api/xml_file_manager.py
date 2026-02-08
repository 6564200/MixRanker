#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления XML файлами
"""

import os
import time
from datetime import datetime
from typing import Dict, List
import logging
from .xml_generator_new import XMLGenerator

logger = logging.getLogger(__name__)


class XMLFileManager:
    """Менеджер XML файлов"""
    
    def __init__(self, output_dir: str = "xml_files"):
        self.output_dir = output_dir
        self.generator = XMLGenerator()
        
        # Создаем директорию если её нет
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_and_save(self, xml_type_info: Dict, tournament_data: Dict, 
                         court_data: Dict = None) -> Dict:
        """Генерирует и сохраняет XML файл"""
        xml_type = xml_type_info.get("type")
        
        # Генерация XML в зависимости от типа
        if xml_type == "tournament_table":
            xml_content = self.generator.generate_tournament_table_xml(tournament_data, xml_type_info)
        elif xml_type == "schedule":
            xml_content = self.generator.generate_schedule_xml(tournament_data)
        elif xml_type == "court_score":
            xml_content = self.generator.generate_court_score_xml(court_data, tournament_data)
        else:
            raise ValueError(f"Неизвестный тип XML: {xml_type}")
        
        # Сохранение файла
        filename = self._get_filename(xml_type_info, tournament_data)
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Информация о файле
        file_stats = os.stat(filepath)
        
        return {
            "id": xml_type_info["id"],
            "name": xml_type_info["name"],
            "filename": filename,
            "url": f"/xml/{filename}",
            "size": self._format_file_size(file_stats.st_size),
            "created": datetime.now().isoformat(),
            "type": xml_type
        }

    def _get_filename(self, xml_type_info: Dict, tournament_data: Dict) -> str:
        """Генерирует имя файла"""
        tournament_id = tournament_data.get("tournament_id", "unknown")
        xml_type = xml_type_info.get("type")
        
        if xml_type == "court_score":
            court_id = xml_type_info.get("court_id", "")
            court_name = xml_type_info.get("court_name", f"court_{court_id}")
            safe_name = "".join(c for c in court_name if c.isalnum() or c in "._-").replace(" ", "_")
            return f"{tournament_id}_court_{court_id}_{safe_name}.xml"
        
        elif xml_type == "tournament_table":
            class_id = xml_type_info.get("class_id", "")
            draw_type = xml_type_info.get("draw_type", "")
            draw_index = xml_type_info.get("draw_index", 0)
            
            if draw_type == "round_robin":
                group_name = xml_type_info.get("group_name", f"group_{draw_index}")
                safe_group = "".join(c for c in group_name if c.isalnum() or c in "._-").replace(" ", "_")
                return f"{tournament_id}_table_{class_id}_rr_{safe_group}.xml"
            else:
                stage_name = xml_type_info.get("stage_name", f"stage_{draw_index}")
                safe_stage = "".join(c for c in stage_name if c.isalnum() or c in "._-").replace(" ", "_")
                return f"{tournament_id}_table_{class_id}_elim_{safe_stage}.xml"
        
        elif xml_type == "schedule":
            return f"{tournament_id}_schedule.xml"
        
        else:
            xml_id = xml_type_info.get("id", "unknown")
            return f"{tournament_id}_{xml_type}_{xml_id}.xml"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Форматирует размер файла"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def generate_all_tournament_xml(self, tournament_data: Dict, courts_data: List[Dict] = None) -> List[Dict]:
        """Генерирует все доступные XML файлы для турнира"""
        from .rankedin_api import RankedinAPI
        
        api = RankedinAPI()
        xml_types = api.get_xml_data_types(tournament_data)
        
        generated_files = []
        
        for xml_type_info in xml_types:
            try:
                xml_type = xml_type_info.get("type")
                
                if xml_type == "court_score":
                    court_id = xml_type_info.get("court_id")
                    if courts_data:
                        court_data = next((c for c in courts_data if str(c.get("court_id")) == str(court_id)), None)
                        if court_data:
                            file_info = self.generate_and_save(xml_type_info, tournament_data, court_data)
                            generated_files.append(file_info)
                else:
                    file_info = self.generate_and_save(xml_type_info, tournament_data)
                    generated_files.append(file_info)
                
            except Exception as e:
                logger.error(f"Ошибка генерации XML {xml_type_info.get('name')}: {e}")
                continue
        
        return generated_files
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Удаляет старые XML файлы"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        removed_count = 0
        
        try:
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.xml'):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = os.path.getmtime(filepath)
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
                        
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов: {e}")
        
        if removed_count > 0:
            logger.info(f"Удалено {removed_count} старых XML файлов")
        
        return removed_count
