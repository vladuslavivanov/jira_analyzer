# Simplified Sequence Diagram (for Presentation)

```mermaid
sequenceDiagram
    actor User as Пользователь<br/>PM / проектный офис
    participant UI as Web UI
    participant Service as Analysis Service
    participant Adapter as Task Source Adapter
    participant Jira as Jira / Mock Jira
    participant Queue as Queue
    participant Worker as LLM Worker
    participant LLM as LLM Provider
    participant DB as SQLite / Storage
    participant Report as Report Generator

    User->>UI: Вводит JQL / ID задачи / Parent ID
    User->>UI: Нажимает «Запустить анализ»

    UI->>Service: createAnalysisRequest(criteria, promptSettings)
    Service->>DB: Создать запуск анализа
    Service->>Adapter: Получить задачи по критерию

    Adapter->>Jira: Запрос задач
    Jira-->>Adapter: Список задач
    Adapter-->>Service: summary, description, type, metadata

    Service->>DB: Сохранить задачи со статусом PENDING
    Service->>Queue: Положить задачи в очередь

    loop Для каждой задачи
        Worker->>Queue: Забрать задачу
        Worker->>DB: Обновить статус PROCESSING
        Worker->>LLM: Отправить prompt + данные задачи + критерии
        LLM-->>Worker: Оценка, диагностика, рекомендации
        Worker->>DB: Сохранить JSON-результат
        Worker->>DB: Обновить статус COMPLETED
    end

    Service->>Report: Сформировать отчет
    Report->>DB: Получить результаты анализа
    DB-->>Report: JSON-результаты
    Report-->>Service: Markdown-отчет + JSON

    Service-->>UI: Вернуть отчет и статус анализа
    UI-->>User: Показать результаты анализа

```
