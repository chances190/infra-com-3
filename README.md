# ChatCin - Terceira Etapa: Sistema de Chat em Grupo com Paradigma Cliente-Servidor  

## Descrição Geral  
O **ChatCin** é um sistema de comunicação que facilita a interação entre estudantes, professores e colaboradores. Nesta terceira etapa, o sistema deve permitir a comunicação entre múltiplos clientes simultaneamente, utilizando sockets UDP com transmissão confiável implementada na camada de aplicação, conforme o protocolo **RDT3.0** descrito no livro *"Redes de Computadores e a Internet"* de Kurose.  

### Requisitos Gerais  
- O sistema deve suportar múltiplos clientes conectados simultaneamente.  
- Cada cliente deve utilizar uma porta única.  
- O servidor deve gerenciar a comunicação entre os clientes e garantir a confiabilidade da transmissão.  
- A interface será baseada em linha de comando.  

### Prazo de Entrega  
- **Data máxima de entrega:** 01/04  
- **Entrega adicional:** Vídeo de até 15 minutos explicando o código e demonstrando o funcionamento do sistema. Todos os integrantes do grupo devem participar.  

---

## Funcionalidades  

### Lista de Contatos  
Exemplo de formato:  
```
Nome               IP:PORTA  
Felipe Maltez      192.168.100.100:5000  
Vitor Azevedo      192.168.100.100:5500  
```  
**Observações:**  
- Cada cliente deve ter um nome único.  
- O IP local pode ser usado como padrão para todos os clientes.  

### Comandos Disponíveis  

| **Funcionalidade**              | **Comando**                              | **Descrição**                                                                                     |  
|----------------------------------|------------------------------------------|---------------------------------------------------------------------------------------------------|  
| Conectar ao sistema             | `login <nome_do_usuario>`                | Conecta o cliente ao sistema. O servidor retorna: "você está online!".                           |  
| Sair do sistema                 | `logout`                                 | Desconecta o cliente e remove-o da lista de usuários online.                                      |  
| Exibir pessoas conectadas       | `list:cinners`                           | Lista todos os usuários conectados no servidor.                                                  |  
| Exibir seus amigos              | `list:friends`                           | Lista os amigos particulares do usuário.                                                         |  
| Exibir seus grupos              | `list:mygroups`                          | Lista os grupos criados pelo usuário, incluindo os nomes e as chaves de cada grupo.              |  
| Exibir grupos que faz parte     | `list:groups`                            | Lista os grupos que o usuário participa, com informações como nome, data de criação e administrador. |  
| Seguir amigo                    | `follow <nome_do_usuario>`               | Adiciona o usuário à lista de amigos seguidos.                                                   |  
| Deixar de seguir amigo          | `unfollow <nome_do_usuario>`             | Remove o usuário da lista de amigos seguidos.                                                    |  
| Criar grupo                     | `create_group <nome_do_grupo>`           | Cria um novo grupo. O servidor retorna: "o grupo de nome <nome_do_grupo> foi criado com sucesso!". |  
| Excluir grupo                   | `delete_group <nome_do_grupo>`           | Exclui um grupo criado pelo usuário.                                                             |  
| Entrar em grupo                 | `join <nome_do_grupo> <chave_grupo>`     | Entra em um grupo utilizando a chave do grupo.                                                   |  
| Sair do grupo                   | `leave <nome_do_grupo>`                  | Sai de um grupo.                                                                                 |  
| Banir amigo de grupo            | `ban <nome_do_usuario>`                  | Remove um usuário do grupo (apenas o administrador pode executar).                               |  
| Conversar no grupo              | `chat_group <nome_grupo> <chave_grupo> <mensagem>` | Envia uma mensagem para todos os membros do grupo.                                               |  
| Conversa particular             | `chat_friend <nome_amigo> <mensagem>`    | Envia uma mensagem privada para um amigo.                                                        |  

---

## Detalhamento das Funcionalidades  

### `login <nome_do_usuario>`  
- O cliente deve fornecer um nome único para se conectar.  
- O servidor retorna: **"você está online!"**.  

### `logout`  
- Remove o cliente da lista de usuários online.  

### `create_group <nome_do_grupo>`  
- Apenas o criador do grupo pode gerenciá-lo.  
- O servidor retorna: **"o grupo de nome <nome_do_grupo> foi criado com sucesso!"**.  

### `delete_group <nome_do_grupo>`  
- Apenas o administrador pode excluir o grupo.  
- Mensagem para os membros: **"[<nome_do_administrador>/<IP>:<SOCKET>] O grupo {nome_do_grupo} foi deletado pelo administrador"**.  

### `join <nome_do_grupo> <chave_grupo>`  
- Valida a chave do grupo antes de permitir a entrada.  
- Mensagem para os membros: **"[<nome_usuário>/<IP>:<SOCKET>] {nome_usuário} acabou de entrar no grupo"**.  

### `leave <nome_do_grupo>`  
- Mensagem para os membros: **"[<nome_usuário>/<IP>:<SOCKET>] {nome_usuário} saiu do grupo"**.  

### `ban <nome_do_usuario>`  
- Apenas o administrador pode banir membros.  
- Mensagem para o banido: **"[<nome_do_administrador>/<IP>:<SOCKET>] O administrador do grupo {nome_do_grupo} o baniu"**.  

### `chat_group <nome_grupo> <chave_grupo> <mensagem>`  
- Envia uma mensagem para todos os membros do grupo, exceto o remetente.  

### `chat_friend <nome_amigo> <mensagem>`  
- Envia uma mensagem privada para um amigo.  

---

## Observações Finais  
- Todos os comandos devem ser interpretados pelo sistema via linha de comando.  
- O servidor deve gerenciar as conexões e garantir a consistência das informações.  
- Mensagens de erro devem ser claras e informativas.  

---  