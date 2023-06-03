from random import shuffle

ColorWhite = [255, 255, 255]
ColorGray = [125, 125, 125]
ColorYellow = [247, 224, 90]
ColorBrown = [205, 107, 29]
ColorPink = [255, 105, 177]
ColorBlue = [49, 162, 242]
ColorPurple = [175, 85, 221]
ColorGreen = [0, 133, 74]

Colors = [ColorWhite, ColorGray, ColorYellow, ColorBrown, ColorPink, ColorBlue, ColorPurple, ColorGreen]
shuffle(Colors)


def next_color():
    i = 0
    while True:
        yield Colors[i]
        i += 1
        if i == len(Colors):
            i = 0


color_generator = next_color()
