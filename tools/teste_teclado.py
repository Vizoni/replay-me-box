import msvcrt

print("Aperte qualquer tecla.")
print("Pressione ESC para sair.")

while True:
    key = msvcrt.getch()

    print(
        "Tecla recebida:",
        repr(key),
        "hex:",
        key.hex()
    )

    if key == b'\x1b':
        break