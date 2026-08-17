"use client"

import { useCallback, useState } from "react"
import { useTranslations } from "next-intl"
import { Search, UserPlus, Trash2, Shield, User } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@intelligent-customer/ui/components/button"
import { Input } from "@intelligent-customer/ui/components/input"
import { Badge } from "@intelligent-customer/ui/components/badge"
import { Card, CardContent } from "@intelligent-customer/ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@intelligent-customer/ui/components/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@intelligent-customer/ui/components/dialog"
import { Label } from "@intelligent-customer/ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@intelligent-customer/ui/components/select"
import useUserServices from "./useServices"

function formatCreatedAt(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return dateStr
  }
}

export default function UsersPage() {
  const t = useTranslations("users")
  const tCommon = useTranslations("common")
  const { users, createControl, createUser, removeUser } = useUserServices()

  const [searchQuery, setSearchQuery] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("user")

  const filteredUsers = users.filter(
    (user) =>
      !searchQuery ||
      user.username.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAddUser = useCallback(async () => {
    try {
      await createUser(username, password, role)
      toast.success(t("addUserSuccess"))
      setAddOpen(false)
      setUsername("")
      setPassword("")
      setRole("user")
    } catch {
      // 错误已由 fetchClient 拦截器统一处理
    }
  }, [createUser, username, password, role, t])

  const handleDeleteUser = useCallback(
    async (id: number) => {
      try {
        await removeUser(id)
        toast.success(t("deleteUserSuccess"))
      } catch {
        // 错误已由 fetchClient 拦截器统一处理
      }
    },
    [removeUser, t]
  )

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("userCount", { count: users.length })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-60 pl-9"
            />
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger
              render={
                <Button>
                  <UserPlus className="mr-2 size-4" />
                  {t("addUser")}
                </Button>
              }
            ></DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("addUserTitle")}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>{t("colUsername")}</Label>
                  <Input
                    placeholder={t("usernamePlaceholder")}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("colPassword")}</Label>
                  <Input
                    type="password"
                    placeholder={t("passwordPlaceholder")}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{t("colRole")}</Label>
                  <Select
                    value={role}
                    onValueChange={(v) => setRole(v ?? "user")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">
                        {tCommon("roleUser")}
                      </SelectItem>
                      <SelectItem value="admin">
                        {tCommon("roleAdmin")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  className="w-full"
                  disabled={createControl.loading}
                  onClick={handleAddUser}
                >
                  {t("addUserConfirm")}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* 用户表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>{t("colUsername")}</TableHead>
                <TableHead>{t("colRole")}</TableHead>
                <TableHead>{t("colCreatedAt")}</TableHead>
                <TableHead className="text-right">{t("colActions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="text-muted-foreground">
                    {user.id}
                  </TableCell>
                  <TableCell className="font-medium">{user.username}</TableCell>
                  <TableCell>
                    <Badge
                      variant={user.role === "admin" ? "default" : "secondary"}
                      className={
                        user.role === "admin"
                          ? "bg-primary/10 text-primary hover:bg-primary/10"
                          : ""
                      }
                    >
                      {user.role === "admin" ? (
                        <>
                          <Shield className="mr-1 size-3" />
                          {tCommon("roleAdmin")}
                        </>
                      ) : (
                        <>
                          <User className="mr-1 size-3" />
                          {tCommon("roleUser")}
                        </>
                      )}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatCreatedAt(user.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="text-destructive hover:text-destructive"
                      disabled={user.role === "admin"}
                      onClick={() => handleDeleteUser(user.id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
