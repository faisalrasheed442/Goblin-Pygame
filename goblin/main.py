import pygame
pygame.init()
#
# character imgs
move_left = [pygame.image.load("Game\L1.png"), pygame.image.load(
    "Game\L2.png"), pygame.image.load("Game\L3.png"), pygame.image.load("Game\L4.png"), pygame.image.load("Game\L5.png"), pygame.image.load("Game\L6.png"), pygame.image.load("Game\L7.png"), pygame.image.load("Game\L8.png"),  pygame.image.load("Game\L9.png")]
move_right = [pygame.image.load('Game\R1.png'), pygame.image.load('Game\R2.png'), pygame.image.load('Game\R3.png'), pygame.image.load('Game\R4.png'), pygame.image.load(
    'Game\R5.png'), pygame.image.load('Game\R6.png'), pygame.image.load('Game\R7.png'), pygame.image.load('Game\R8.png'), pygame.image.load('Game\R9.png')]
win = pygame.display.set_mode((500, 500))
bg = pygame.image.load("Game\\bg1.jpg")
standing = pygame.image.load("Game\standing.png")

score=0
bulletsound=pygame.mixer.Sound("Game\\bullet.wav")
bullethit=pygame.mixer.Sound("Game\\hit.wav")
bg_music = pygame.mixer.music.load("Game\music.mp3")
pygame.mixer.music.play(-1)
class player(object):
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.velocity = 5
        self.jump = False
        self.left = False
        self.right = False
        self.jumpcount = 8
        self.count = 0
        self.standing = False
        self.hitbox = (self.x+20, self.y+12, 28, 50)
        self.ss=0


    def draw(self, win):
        if self.count >= 27:
            self.count = 0

        if not (self.standing):
            if self.left:
                win.blit(move_left[self.count//3], (self.x, self.y))
                self.count += 1
            elif self.right:
                win.blit(move_right[self.count//3], (self.x, self.y))
                self.count += 1
        else:
            if self.left:
                win.blit(move_left[0], (self.x, self.y))
            else:
                win.blit(move_right[0], (self.x, self.y))
            self.count = 0
        self.hitbox = (self.x+20, self.y+12, 28, 50)
        # pygame.draw.rect(win, (255, 0, 0), self.hitbox, 2)
# 
    def hiit(self):
        self.x=60
        self.count=0
        font1=pygame.font.SysFont("comicsans",100)
        text=font1.render("-5",1,(255,0,0))
        win.blit(text,(200,300))
        pygame.display.update()
        i=0
        while i<100:
            pygame.time.delay(10)
            i+=1
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    pygame.quit()
        print("hit men",self.ss)




class projectile(object):
    def __init__(self, x, y, radius, facing, color):
        self.x = x
        self.y = y
        self.radius = radius
        self.facing = facing
        self.color = color
        self.vel = 8 * self.facing

    def draw(self, win):
        pygame.draw.circle(win, self.color, (self.x, self.y), self.radius)


class enemy(object):
    walkRight = [pygame.image.load('Game\R1E.png'), pygame.image.load('Game\R2E.png'), pygame.image.load('Game\R3E.png'), pygame.image.load('Game\R4E.png'), pygame.image.load('Game\R5E.png'), pygame.image.load(
        'Game\R6E.png'), pygame.image.load('Game\R7E.png'), pygame.image.load('Game\R8E.png'), pygame.image.load('Game\R9E.png'), pygame.image.load('Game\R10E.png'), pygame.image.load('Game\R11E.png')]
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    walkLeft = [pygame.image.load('Game\L1E.png'), pygame.image.load('Game\L2E.png'), pygame.image.load('Game\L3E.png'), pygame.image.load('Game\L4E.png'), pygame.image.load('Game\L5E.png'), pygame.image.load(
        'Game\L6E.png'), pygame.image.load('Game\L7E.png'), pygame.image.load('Game\L8E.png'), pygame.image.load('Game\L9E.png'), pygame.image.load('Game\L10E.png'), pygame.image.load('Game\L11E.png')]

    def __init__(self, x, y, width, height, end):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.end = end
        self.path = [self.x, self.end]
        self.walkcount = 0
        self.vel = 3
        self.hitbox = (self.x+20, self.y+3, 28, 50)
        self.hitt=0
        self.start = False
        self.redraw=True
        self.health=10
    def draw(self, win):
        self.move()
        if self.redraw:
            self.redraw=True
            if self.walkcount+1 >= 33:
                self.walkcount = 0
            if self.vel > 0:
                win.blit(self.walkRight[self.walkcount//3], (self.x, self.y))
                self.walkcount += 1
            else:
                win.blit(self.walkLeft[self.walkcount//3], (self.x, self.y))
                self.walkcount += 1
            self.hitbox = (self.x+20, self.y+3, 28, 50)
            # pygame.draw.rect(win, (255, 0, 0), self.hitbox, 2)
            if score==0:
                pygame.draw.rect(win, (12, 148, 3, 1.00),(self.x+20, self.y-10, 30, 10), 0)
            else:
                if score>=10:
                    self.hitt=0
                    pygame.draw.rect(win, (12, 148, 3, 1.00),(self.x+20, self.y-10, 30, 10), 0)
                while self.start:
                    self.hitt+=3
                    self.start=False
                pygame.draw.rect(win, (12, 148, 3, 1.00),(self.x+20, self.y-10, 30, 10), 0)
                pygame.draw.rect(win,(255,0,0),(self.x+20,self.y-10,self.hitt,10),0)

    def move(self):
        if self.vel > 0:
            if self.x+self.vel < self.path[1]:
                self.x += self.vel
            else:
                self.vel = self.vel * -1
                self.walkcount = 0
        else:
            if self.x > self.path[0]-self.vel:
                self.x += self.vel
            else:
                self.vel = self.vel * -1
                self.walkcount = 0

    def hit(self):
        if self.health>0:
            self.health-=1
        else:
            self.redraw=False
        self.start=True

# movine speed
clock = pygame.time.Clock()
#
# moving
man = player(100, 395, 64, 64)
goblin = enemy(200, 400, 64, 64, 350)
# drwaing function


def drawing():
    win.blit(bg, (0, 0))
    text=font.render("Score: "+str(score),1,(0,0,0))
    win.blit(text,(10,10))
    man.draw(win)
    goblin.draw(win)
    for bullet in bullets:
        bullet.draw(win)
    pygame.display.update()

# main loop
font=pygame.font.SysFont('gotham bold',40)
shoot_bullet = 0
bullets = []
i=0
run = True
import math
while run:
    
    clock.tick(27)
    if goblin.redraw==True:
        if man.hitbox[0]+man.hitbox[2]>goblin.hitbox[0]and man.hitbox[0]<goblin.hitbox[0]+goblin.hitbox[2]:
            if man.hitbox[1]>goblin.hitbox[1]:
                score-=5
                man.hiit()
    goblin.move()
    if shoot_bullet > 0:
        shoot_bullet += 1
    if shoot_bullet > 3:
        shoot_bullet = 0                            
    for bullet in bullets:
        if goblin.redraw==True:
            if bullet.x+bullet.radius>goblin.hitbox[0] and bullet.x-bullet.radius-20<goblin.hitbox[0]:
                if bullet.y>goblin.hitbox[1]:
                    bullethit.play()
                    goblin.hit()
                    score+=1
                    bullets.pop(bullets.index(bullet))
        if bullet.x < 500 and bullet.x > 0:
            bullet.x += bullet.vel
        else:
            bullets.pop(bullets.index(bullet))
    for events in pygame.event.get():
        if events.type == pygame.QUIT:
            run = False
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE] and shoot_bullet == 0:
        bulletsound.play()
        if man.left:
            facing = -1
        else:
            facing = 1
        if len(bullets) <= 5:
            bullets.append(projectile(round(man.x+man.width//2),
                round(man.y+man.height//2), 6, facing, (0, 0, 0)))
        shoot_bullet = 1
    if keys[pygame.K_LEFT] and man.x >= 5:
        man.x -= man.velocity
        man.left = True
        man.right = False
        man.standing = False
    elif keys[pygame.K_RIGHT] and man.x <= 436:
        man.x += man.velocity
        man.left = False
        man.right = True
        man.standing = False
    else:
        man.standing = True
        man.count = 0
    if not man.jump:
        if keys[pygame.K_UP]:
            man.jump = True
    else:
        if man.jumpcount >= -8:
            neg = 1
            if man.jumpcount < 0:
                neg = -1
            man.y -= (man.jumpcount**2)*neg
            man.jumpcount -= 1
        else:
            man.jump = False
            man.jumpcount = 8
    drawing()
pygame.quit()
