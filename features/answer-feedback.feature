Feature: Feedback del usuario sobre las respuestas
  Como usuario del chat quiero indicar si una respuesta me fue útil
  para que ese voto quede registrado en Langfuse junto a la traza de la consulta.

  @s1
  Scenario: La consulta devuelve el trace_id cuando el tracing está habilitado
    Given que el tracing de Langfuse está habilitado y la traza de la consulta tiene id "4bf92f3577b34da6a3ce929d0e0e4736"
    When el cliente envía POST /api/query con una pregunta válida
    Then la respuesta tiene status 200
    And query_result.trace_id es "4bf92f3577b34da6a3ce929d0e0e4736"

  @s2
  Scenario: La consulta devuelve trace_id null cuando el tracing está deshabilitado
    Given que el tracing de Langfuse está deshabilitado
    When el cliente envía POST /api/query con una pregunta válida
    Then la respuesta tiene status 200
    And query_result.trace_id es null

  @s3
  Scenario: Un voto útil se registra como score BOOLEAN sobre la traza
    Given que el tracing de Langfuse está habilitado
    When el cliente envía POST /api/feedback con {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "helpful": true}
    Then la respuesta tiene status 200
    And el body es {"feedback_result": {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "helpful": true}}
    And se crea en Langfuse un score con name "user_feedback", data_type "BOOLEAN" y value 1 sobre el trace "4bf92f3577b34da6a3ce929d0e0e4736"
    And el score_id se deriva de forma determinística del trace_id

  @s4
  Scenario: Un re-voto pisa el voto anterior en lugar de acumularse
    Given que el tracing de Langfuse está habilitado
    And que ya se registró un voto helpful true para el trace "4bf92f3577b34da6a3ce929d0e0e4736"
    When el cliente envía POST /api/feedback con {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "helpful": false}
    Then la respuesta tiene status 200
    And se envía a Langfuse un score "user_feedback" con value 0 y el mismo score_id que el voto anterior
    And no se crea un segundo score distinto para ese trace

  @s5
  Scenario: Un request inválido se rechaza con 422
    Given que el tracing de Langfuse está habilitado
    When el cliente envía POST /api/feedback con un trace_id que no tiene 32 caracteres hexadecimales, o sin el campo helpful booleano
    Then la respuesta tiene status 422
    And el body tiene la forma {"error": <texto>}
    And no se envía ningún score a Langfuse

  @s6
  Scenario: Con el tracing deshabilitado el feedback responde 503
    Given que el tracing de Langfuse está deshabilitado
    When el cliente envía POST /api/feedback con {"trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "helpful": true}
    Then la respuesta tiene status 503
    And el body es {"error": "Tracing deshabilitado: el feedback no se registró"}
