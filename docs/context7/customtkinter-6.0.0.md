> 版本: 6.0.0 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Create a basic CustomTkinter application

Source: https://github.com/tomschimansky/customtkinter/blob/master/Readme.md

Initializes a window with a single button using the CTkButton widget.

```python
import customtkinter

customtkinter.set_appearance_mode("System")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green

app = customtkinter.CTk()  # create CTk window like you do with the Tk window
app.geometry("400x240")

def button_function():
    print("button pressed")

# Use CTkButton instead of tkinter Button
button = customtkinter.CTkButton(master=app, text="CTkButton", command=button_function)
button.place(relx=0.5, rely=0.5, anchor=customtkinter.CENTER)

app.mainloop()
```

--------------------------------

### CTkSwitch Constructor

Source: https://github.com/tomschimansky/customtkinter/wiki/CTkSwitch

Initializes a new CTkSwitch widget instance.

```APIDOC
## CTkSwitch(master, **kwargs)

### Description
Creates a new switch widget instance.

### Arguments
- **master** (widget) - The parent widget.
- **width** (int) - Width of complete widget in px.
- **height** (int) - Height of complete widget in px.
- **switch_width** (int) - Width of switch in px.
- **switch_height** (int) - Height of switch in px.
- **corner_radius** (int) - Corner radius in px.
- **border_width** (int) - Box border width in px.
- **fg_color** (tuple/str) - Foreground color.
- **border_color** (tuple/str) - Border color.
- **progress_color** (tuple/str) - Color of switch when enabled.
- **button_color** (tuple/str) - Color of button.
- **button_hover_color** (tuple/str) - Hover color of button.
- **hover_color** (tuple/str) - Hover color.
- **text_color** (tuple/str) - Text color.
- **text** (str) - Display text.
- **textvariable** (StringVar) - Tkinter variable to control text.
- **font** (tuple) - Text font.
- **command** (callable) - Function called on toggle.
- **variable** (Variable) - Tkinter variable to control state.
- **onvalue** (str/int) - Value for checked state.
- **offvalue** (str/int) - Value for unchecked state.
- **state** (str) - 'normal' or 'disabled'.
```

--------------------------------

### customtkinter.CTkButton(master, **kwargs)

Source: https://github.com/tomschimansky/customtkinter/wiki/CTkButton

Initializes a new CTkButton instance. The button supports various styling and functional arguments.

```APIDOC
## customtkinter.CTkButton(master, **kwargs)

### Description
Creates a new button widget. The button can be customized with dimensions, colors, text, and command callbacks.

### Arguments
- **master** (root, tkinter.Frame, or CTkFrame) - Required - The parent widget.
- **width** (int) - Optional - Button width in px.
- **height** (int) - Optional - Button height in px.
- **corner_radius** (int) - Optional - Corner radius in px.
- **border_width** (int) - Optional - Button border width in px.
- **border_spacing** (int) - Optional - Spacing between text/image and border (default: 2).
- **fg_color** (tuple/str) - Optional - Foreground color.
- **hover_color** (tuple/str) - Optional - Hover color.
- **border_color** (tuple/str) - Optional - Border color.
- **text_color** (tuple/str) - Optional - Text color.
- **text_color_disabled** (tuple/str) - Optional - Text color when disabled.
- **text** (str) - Optional - Button text.
- **font** (tuple) - Optional - Font settings (name, size).
- **textvariable** (tkinter.StringVar) - Optional - Variable to track button text.
- **image** (PhotoImage) - Optional - Image to display on the button.
- **state** (str) - Optional - "normal" or "disabled".
- **hover** (bool) - Optional - Enable/disable hover effect.
- **command** (callable) - Optional - Callback function.
- **compound** (str) - Optional - Image orientation ("top", "left", "bottom", "right").
- **anchor** (str) - Optional - Alignment ("n", "ne", "e", "se", "s", "sw", "w", "nw", "center").
```

--------------------------------

### CTkLabel Constructor

Source: https://github.com/tomschimansky/customtkinter/wiki/CTkLabel

Initializes a new CTkLabel widget.

```APIDOC
## CTkLabel(master, **kwargs)

### Description
Creates a new label widget within the specified master container.

### Arguments
- **master** (object) - Required - The parent widget (root, CTkFrame, etc.)
- **text** (string) - Optional - The text to display.
- **textvariable** (StringVar) - Optional - A tkinter.StringVar object to link to the label text.
- **width** (int) - Optional - Width in pixels.
- **height** (int) - Optional - Height in pixels.
- **corner_radius** (int) - Optional - Corner radius in pixels.
- **fg_color** (tuple/str) - Optional - Foreground color (light, dark) or single color.
- **text_color** (tuple/str) - Optional - Text color (light, dark) or single color.
- **font** (tuple) - Optional - Font settings (name, size).
- **anchor** (str) - Optional - Text alignment within the widget.
- **compound** (str) - Optional - Position of image relative to text.
- **justify** (str) - Optional - Alignment of multiple lines (left, center, right).
- **padx** (int) - Optional - Horizontal padding.
- **pady** (int) - Optional - Vertical padding.
```

--------------------------------

### CTkEntry Constructor

Source: https://github.com/tomschimansky/customtkinter/wiki/CTkEntry

Initializes a new CTkEntry widget instance.

```APIDOC
## CTkEntry(master, **kwargs)

### Description
Creates a new entry widget instance within the specified master container.

### Parameters
- **master** (root, tkinter.Frame, or CTkFrame) - Required - The parent widget.
- **textvariable** (tkinter.StringVar) - Optional - Variable to link with the entry content.
- **width** (int) - Optional - Width in pixels.
- **height** (int) - Optional - Height in pixels.
- **corner_radius** (int) - Optional - Corner radius in pixels.
- **fg_color** (tuple/str) - Optional - Foreground color.
- **text_color** (tuple/str) - Optional - Text color.
- **placeholder_text_color** (tuple/str) - Optional - Color of the placeholder text.
- **placeholder_text** (str) - Optional - Hint text displayed when empty.
- **font** (tuple) - Optional - Font settings (name, size).
- **state** (str) - Optional - 'normal' or 'disabled'.
```