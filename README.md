# Mad King Redemption no ROG Ally

Ajustes locais para o build Steam 26417954 em Bazzite com Proton.

- O jogo grava ouro ganho ou gasto e novos desbloqueios no slot carregado. A abertura usa a leitura normal do slot.
- O primeiro pulo sai do chão. Pressione **A** mais duas vezes no ar antes de aterrissar. O contador é recarregado nas transições de movimento em terra.
- No mapeamento padrão, **Y** dispara o ataque à distância.
- Se a DLL já estiver com vidas infinitas, os dois novos ajustes preservam esse patch.

`ajustes-mad-king.py` aplica os ajustes a uma DLL compatível do próprio usuário. `ajustes-mad-king.s` contém o código-fonte dos trechos de máquina usados pelo aplicador. A pasta `backups` no Ally mantém a DLL anterior e uma cópia do save anterior à mudança.

## Reaplicar no Bazzite

Para reproduzir a configuração testada, coloque os scripts em `~/Games/MadKingRedemption`, feche o jogo e faça uma cópia do slot. Antes de aplicar o pulo e o autosave, execute o ajuste de vidas sobre a DLL da sua instalação.

```bash
base="$HOME/.local/share/Steam/steamapps/common/Mad King Redemption/Mad King Redemption"
mods="$HOME/Games/MadKingRedemption"
mkdir -p "$mods/backups"
python3 "$mods/vidas-infinitas.py" "$base/GameAssembly.dll" "$mods/backups/GameAssembly-26417954.original.dll"
```

```bash
base="$HOME/.local/share/Steam/steamapps/common/Mad King Redemption/Mad King Redemption"
mods="$HOME/Games/MadKingRedemption"
python3 "$mods/ajustes-mad-king.py" "$base/GameAssembly.dll" "$mods/backups/GameAssembly-26417954.pre-ajustes.dll"
```

Para restaurar a DLL anterior, use o mesmo comando com `--restore` ao final. A restauração da DLL independe dos arquivos de progresso. Uma atualização da Steam pode substituir a DLL. O aplicador verifica o hash antes de aceitar uma versão.

## Recriar os trechos de máquina

```bash
as -o ajustes-mad-king.o ajustes-mad-king.s
ld -Ttext=0x4842000 -e autosave_frame \
  --defsym=run_metadata_ready=0x41ad136 \
  --defsym=game_metadata_ready=0x41ac7ff \
  --defsym=run_class=0x3f63c68 --defsym=game_class=0x3ef6880 \
  --defsym=autosave_state=0x446b960 --defsym=native_save_game=0x75c4f0 \
  --defsym=native_persistent_gold=0x6f57d0 \
  -o ajustes-mad-king.elf ajustes-mad-king.o
objcopy -O binary --only-section=.text ajustes-mad-king.elf ajustes-mad-king.bin
base64 -w0 ajustes-mad-king.bin
```


## Ouro infinito

No build Steam 26417954, a carteira da partida e o saldo salvo usam inteiros de 32 bits. O ajuste fixa a carteira em **2.147.483.647**. A loja continua registrando o preço nas estatísticas e o ouro recolhido continua contando como ganho. O saldo disponível para gastar permanece no máximo.

Aplique depois dos ajustes de vidas, pulo e autosave descritos acima. Feche e reabra o jogo para carregar a alteração.

```bash
python3 "$mods/ouro-infinito.py" "$base/GameAssembly.dll" "$mods/backups/GameAssembly-26417954.pre-ouro.dll"
```

Para voltar às regras normais de ganho e gasto, repita o comando com `--restore`. Restaurar a DLL mantém o saldo já gravado no slot. Para recuperar o saldo anterior, use a cópia do save correspondente com o jogo fechado. O teste no Ally conferiu o saldo na tela após carregar o primeiro slot. Os testes isolados cobriram gasto de 68 e 1.200 moedas e recebimento de ouro.
