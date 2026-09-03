# 小程序常见接口字典

## 用户态 ID 参数

```
userId uid memberId openid customerId accountId
orderId shopId productId addressId cardId billId
invoiceId ticketId couponId prizeId
mobile phone email idCard
```

## 敏感参数关键词

```
token secret password passwd
appsecret app_secret AppSecret
apikey api_key accesskey access_key
session session_key sessionKey
privatekey private_key
env cloud cloudEnv
```

## 支付/业务参数

```
amount price money fee totalFee total_amount
count num quantity stock
status state type level
couponId discountId activityId
withdrawAmount rechargeAmount balance
```

## WebView/路由参数

```
url src link redirect target callback
webviewUrl page path href navigate
```

## 常见 API 路径模式

```
/api/user/*
/api/order/*
/api/product/*
/api/address/*
/api/coupon/*
/api/pay/*
/api/auth/*
/api/login
/api/register
/api/reset
/api/withdraw/*
/api/admin/*
/api/manage/*
```

## wx API 调用模式

```javascript
wx.request({url, data, header, method})
wx.uploadFile({url, filePath, name, header, formData})
wx.downloadFile({url, header})
wx.setStorageSync(key, data)
wx.getStorageSync(key)
wx.navigateTo({url})
wx.redirectTo({url})
wx.login()
wx.getUserInfo()
wx.getUserProfile()
wx.chooseAddress()
wx.getPhoneNumber()
wx.cloud.callFunction({name, data})
wx.cloud.database()
```
